import json
from odoo import models, fields, api, exceptions,_
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError

class InheritAccountPayment(models.Model):
    _inherit = 'account.payment'

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable', 'other')), ('company_id', '=', company_id)]",
        check_company=True)

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        res = super(InheritAccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
        global_tax_enabled = self.env['ir.config_parameter'].sudo().get_param('account.global_taxes') or False
        
        # Fixed condition: Check if write_off_line_vals is not None before accessing keys
        if global_tax_enabled and write_off_line_vals and write_off_line_vals.get('global_tax'):
            res = super(InheritAccountPayment, self)._prepare_move_line_default_vals()
            if self.payment_type == 'inbound':
                # Receive money.
                mod = 1
                liquidity_amount_currency = self.amount
            elif self.payment_type == 'outbound':
                # Send money.
                liquidity_amount_currency = -self.amount
                mod = -1
            
            # Use .get() to avoid KeyError if amount is missing
            write_off_amount_currency = write_off_line_vals.get('amount', 0.0)
            write_off_amount_currency *= mod
            write_off_balance = self.currency_id._convert(
                write_off_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
            counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
            counterpart_balance = -liquidity_balance - write_off_balance
            currency_id = self.currency_id.id

            if self.is_internal_transfer:
                if self.payment_type == 'inbound':
                    liquidity_line_name = _('Transfer to %s', self.journal_id.name)
                else: # payment.payment_type == 'outbound':
                    liquidity_line_name = _('Transfer from %s', self.journal_id.name)
            else:
                liquidity_line_name = self.payment_reference

            payment_display_name = self._prepare_payment_display_name()

            default_line_name = self.env['account.move.line']._get_default_line_name(
                _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
                self.amount,
                self.currency_id,
                self.date,
                partner=self.partner_id,
            )

            res = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': liquidity_amount_currency,
                    'currency_id': currency_id,
                    'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                    'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.journal_id.payment_credit_account_id.id if liquidity_balance < 0.0 else self.journal_id.payment_debit_account_id.id,
                },
                
            ]
            if not self.currency_id.is_zero(write_off_amount_currency):
                # Write-off line.
                res.append({
                    'name': write_off_line_vals.get('name') or default_line_name,
                    'amount_currency': write_off_amount_currency,
                    'currency_id': currency_id,
                    'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                    'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': write_off_line_vals.get('account_id'),
                })
            
            # Safe to access global_tax now because of the if condition above
            for tax in write_off_line_vals['global_tax']:
                amount = tax['amount'] * mod
                counterpart_amount_currency -= amount
                tax_balance = self.currency_id._convert(
                    amount,
                    self.company_id.currency_id,
                    self.company_id,
                    self.date,
                )
                counterpart_balance -= tax_balance
                res.append({
                    'name': tax['name'],
                    'amount_currency': amount,
                    'currency_id': tax['currency_id'],
                    'debit': tax_balance if tax_balance > 0.0 else 0.0,
                    'credit': -tax_balance if tax_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': tax['account_id'],
                })
            res.append(
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                    'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.destination_account_id.id,
                },
            )
        
        return res

    def _synchronize_from_moves(self, changed_fields):
        # (metode ini tidak diubah dan seharusnya tidak menyebabkan error saat ini)
        
        # ... (kode _synchronize_from_moves tidak diubah)
        # Hapus bagian ini jika tidak diperlukan, karena tidak ada masalah di sini saat ini.
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal entry must always contains:\n"
                        "- one journal item involving the outstanding payment/receipts account.\n"
                        "- one journal item involving a receivable/payable account.\n"
                        "- optional journal items, all sharing the same account.\n\n"
                    ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if not pay.is_internal_transfer:
                    if counterpart_lines.account_id.user_type_id.type == 'receivable':
                        payment_vals_to_write['partner_type'] = 'customer'
                    else:
                        payment_vals_to_write['partner_type'] = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))
