# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import logging
_logger = logging.getLogger(__name__)

class AccountYearEndClosingWizardLine(models.TransientModel):
    _name = 'account.year_end_closing.wizard.line'
    _description = 'Year-End Closing Wizard Line'

    wizard_id = fields.Many2one('account.year_end_closing.wizard', string='Wizard')
    account_id = fields.Many2one('account.account', string='Account')
    balance = fields.Float(string='Balance')

class AccountYearEndClosingWizard(models.TransientModel):
    _name = 'account.year_end_closing.wizard'
    _description = 'Year-End Closing Wizard'

    year = fields.Integer(string='Fiscal Year to Close', required=True, default=lambda self: fields.Date.today().year - 1)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    state = fields.Selection([('init', 'Initiate'), ('preview', 'Preview')], default='init')
    total_balance = fields.Float(string='Calculated Profit/Loss', readonly=True)
    message = fields.Text(string='Analysis Result', readonly=True)
    line_ids = fields.One2many('account.year_end_closing.wizard.line', 'wizard_id', string='Account Details', readonly=True)

    def action_calculate_balance(self):
        self.ensure_one()
        company = self.company_id
        year = self.year
        
        # Validation 1: Configuration
        if not company.retained_earnings_account_id:
            raise UserError(_("Please configure the Retained Earnings Account in Accounting Settings first."))
        
        # Validation 2: Draft Moves (Check all previous periods up to date_to)
        date_to = datetime.date(year, 12, 31)
        # Use sudo() to ensure we find moves that might be hidden by Record Rules
        unposted_moves = self.env['account.move'].sudo().search([
            ('company_id', '=', company.id),
            ('date', '<=', date_to),
            ('state', 'not in', ['posted', 'cancel'])
        ], limit=10) # Limit to 10 for display
        if unposted_moves:
            details = "\n".join(["- %s (%s) - State: %s" % (m.name or m.ref or 'New', m.date, m.state) for m in unposted_moves])
            raise UserError(_("There are Unposted Entries on or before %s. Odoo will block the fiscal year lock until these are posted or deleted:\n\n%s") % (date_to, details))

        # Logic: Calculate balances
        # Broaden detection to all P&L types
        nominal_accounts = self.env['account.account'].sudo().search([
            ('company_id', '=', company.id),
            '|', ('internal_group', 'in', ['income', 'expense']),
            ('user_type_id.type', 'in', ['income', 'other_income', 'expenses', 'depreciation', 'cost_of_revenue'])
        ])
        
        total_balance = 0.0
        account_count = 0
        preview_lines = []
        for account in nominal_accounts:
            self._cr.execute("""
                SELECT sum(debit) - sum(credit) 
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.account_id = %s 
                  AND aml.company_id = %s
                  AND aml.date <= %s
                  AND am.state = 'posted'
            """, (account.id, company.id, date_to))
            balance = self._cr.fetchone()[0] or 0.0
            if not company.currency_id.is_zero(balance):
                total_balance += balance
                account_count += 1
                preview_lines.append((0, 0, {
                    'account_id': account.id,
                    'balance': balance,
                }))

        self.write({
            'state': 'preview',
            'total_balance': total_balance,
            'line_ids': preview_lines,
            'message': _("Analysis for Fiscal Year %s complete.\nFound %s accounts with balances.\nNet Profit/Loss: %s %s\nTarget Lock Date: %s\nNote: Transactions after %s are NOT included.") % (
                year, account_count, total_balance, company.currency_id.symbol, date_to, date_to)
        })
        return {
            'name': _('Year-End Closing Agent'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.year_end_closing.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_closing_entry(self):
        self.ensure_one()
        company = self.company_id
        year = self.year
        
        # Validation 1: Configuration
        if not company.retained_earnings_account_id:
            raise UserError(_("Please configure the Retained Earnings Account in Accounting Settings first."))
        if not company.closing_journal_id:
            raise UserError(_("Please configure the Closing Journal in Accounting Settings first."))

        # Validation 2: Draft Moves (Check all previous periods up to date_to)
        date_to = datetime.date(year, 12, 31)
        # Use sudo() to find hidden moves
        unposted_moves = self.env['account.move'].sudo().search([
            ('company_id', '=', company.id),
            ('date', '<=', date_to),
            ('state', 'not in', ['posted', 'cancel'])
        ], limit=10)
        if unposted_moves:
            details = "\n".join(["- %s (%s) - State: %s" % (m.name or m.ref or 'New', m.date, m.state) for m in unposted_moves])
            raise UserError(_("There are Unposted Entries on or before %s. Please post or delete them before closing the year:\n\n%s") % (date_to, details))

        # Validation 3: Existing Closing
        existing_closing = self.env['account.year_end.closing'].search([
            ('company_id', '=', company.id),
            ('year', '=', year),
            ('state', '!=', 'cancelled')
        ])
        if existing_closing:
             raise UserError(_("A closing entry for %s already exists.") % year)

        # Logic: Get balances for nominal accounts
        # Nominal accounts in Odoo 14 have internal_group as 'income' or 'expense'
        nominal_accounts = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('internal_group', 'in', ['income', 'expense'])
        ])
        
        move_lines = []
        total_balance = 0.0

        for account in nominal_accounts:
            # Get balance as of Dec 31
            self._cr.execute("""
                SELECT sum(debit) - sum(credit) 
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                WHERE aml.account_id = %s 
                  AND aml.company_id = %s
                  AND aml.date <= %s
                  AND am.state = 'posted'
            """, (account.id, company.id, date_to))
            balance = self._cr.fetchone()[0] or 0.0
            
            if company.currency_id.is_zero(balance):
                continue
            
            # Create reversing line
            line_label = _("Closing of %s for Fiscal Year %s") % (account.name, year)
            
            # If balance is 100 (Debit), we need to Credit 100
            # If balance is -100 (Credit), we need to Debit 100
            move_lines.append((0, 0, {
                'name': line_label,
                'account_id': account.id,
                'debit': abs(balance) if balance < 0 else 0.0,
                'credit': balance if balance > 0 else 0.0,
            }))
            total_balance += balance

        if not move_lines:
            raise UserError(_("No balances found in Income and Expense accounts for the year %s.") % year)

        # Difference goes to Retained Earnings
        # If total_balance is 1000 (Profit), we need to Debit 1000 to nominal and Credit 1000 to Retained Earnings
        retained_label = _("Net Profit/Loss transfer for Fiscal Year %s") % year
        move_lines.append((0, 0, {
            'name': retained_label,
            'account_id': company.retained_earnings_account_id.id,
            'debit': total_balance if total_balance > 0 else 0.0,
            'credit': abs(total_balance) if total_balance < 0 else 0.0,
        }))

        # Create the move in Draft
        move_vals = {
            'ref': 'YEC/%s/KM' % year,
            'journal_id': company.closing_journal_id.id,
            'date': date_to,
            'line_ids': move_lines,
            'state': 'draft',
            'move_type': 'entry'
        }
        closing_move = self.env['account.move'].create(move_vals)
        
        # Create history record
        closing_history = self.env['account.year_end.closing'].create({
            'year': year,
            'company_id': company.id,
            'move_id': closing_move.id,
        })

        # Return action to view the created move

        # Return action to view the created move
        return {
            'name': _('Draft Closing Entry Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': closing_move.id,
            'view_mode': 'form',
            'target': 'current',
        }
