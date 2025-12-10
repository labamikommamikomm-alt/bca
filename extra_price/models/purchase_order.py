# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

# =============================================================================
# Model untuk menampung data Extra Price di Purchase Order
# =============================================================================
class PurchaseOrderExtraPrice(models.Model):
    _name = 'purchase.order.extra.price'
    _description = 'Purchase Order Extra Price Line'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order Reference',
        required=True,
        ondelete='cascade'
    )
    label = fields.Char(
        string='Label',
        required=True
    )
    account_id = fields.Many2one(
        'account.account',
        string='Akun Biaya',
        required=True,
        domain=[('deprecated', '=', False), ('user_type_id.type', 'not in', ('receivable', 'payable'))]
    )
    amount = fields.Monetary(
        string='Amount',
        required=True
    )
    currency_id = fields.Many2one(
        related='purchase_order_id.currency_id',
        store=True,
        string='Currency'
    )

# =============================================================================
# Logika pembuatan Bill dan Journal Entry dari Purchase Order
# =============================================================================
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    extra_price_line_ids = fields.One2many('purchase.order.extra.price', 'purchase_order_id', string='Extra Price Lines', copy=True)

    grand_total_with_costs = fields.Monetary(
        string="Grand Total",
        compute='_compute_grand_total_with_costs',
        store=True
    )

    @api.depends('amount_total', 'extra_price_line_ids.amount')
    def _compute_grand_total_with_costs(self):
        for po in self:
            extra_costs = sum(po.extra_price_line_ids.mapped('amount'))
            po.grand_total_with_costs = po.amount_total + extra_costs

    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        main_bill = self.env['account.move'].browse(res.get('res_id')) or self.invoice_ids.filtered(lambda m: m.state == 'draft')[:1]
        if not main_bill:
            return res

        if self.extra_price_line_ids:
            misc_journal = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
            if not misc_journal:
                raise UserError(_("Harap konfigurasikan Jurnal 'Miscellaneous Operations' untuk perusahaan Anda."))
            
            total_extra_cost = sum(self.extra_price_line_ids.mapped('amount'))
            journal_lines = []
            journal_lines.append((0, 0, {
                'account_id': main_bill.partner_id.property_account_payable_id.id,
                'partner_id': self.partner_id.id,
                'name': f"Biaya Tambahan: {self.name}",
                'credit': total_extra_cost,
                'debit': 0,
            }))
            for line in self.extra_price_line_ids:
                journal_lines.append((0, 0, {
                    'account_id': line.account_id.id,
                    'partner_id': self.partner_id.id,
                    'name': line.label,
                    'credit': 0,
                    'debit': line.amount,
                }))

            extra_cost_journal = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': misc_journal.id,
                'partner_id': self.partner_id.id,
                'date': fields.Date.context_today(self),
                'ref': f"Biaya Tambahan untuk {self.name}",
                'line_ids': journal_lines,
            })
            main_bill.write({'extra_cost_journal_id': extra_cost_journal.id})

        return self.action_view_invoice()

# =============================================================================
# Modifikasi Account Move (Vendor Bill)
# =============================================================================
class AccountMove(models.Model):
    _inherit = 'account.move'

    extra_cost_journal_id = fields.Many2one('account.move', string="Extra Costs Journal", readonly=True, copy=False)
    grand_total_with_costs = fields.Monetary(string="Grand Total", compute='_compute_combined_totals', store=True)
    residual_with_costs = fields.Monetary(string="Amount Due", compute='_compute_combined_totals', store=True)

    @api.depends(
        'amount_total', 'amount_residual',
        'extra_cost_journal_id.state',
        'extra_cost_journal_id.line_ids.amount_residual'
    )
    def _compute_combined_totals(self):
        for bill in self:
            extra_cost_total = 0
            extra_cost_residual = 0
            if bill.extra_cost_journal_id and bill.extra_cost_journal_id.state == 'posted':
                extra_cost_total = bill.extra_cost_journal_id.amount_total
                payable_line = bill.extra_cost_journal_id.line_ids.filtered(
                    lambda l: l.account_id.internal_type == 'payable' and not l.reconciled
                )
                extra_cost_residual = sum(payable_line.mapped('amount_residual'))
            bill.grand_total_with_costs = bill.amount_total + extra_cost_total
            bill.residual_with_costs = bill.amount_residual + abs(extra_cost_residual)

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.extra_cost_journal_id and move.extra_cost_journal_id.state == 'draft':
                move.extra_cost_journal_id.action_post()
        return res

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            if move.extra_cost_journal_id and move.extra_cost_journal_id.state == 'posted':
                move.extra_cost_journal_id.button_draft()
        return res
    
    def action_register_payment(self):
        action = super(AccountMove, self).action_register_payment()
        action['context'].update({
            'default_amount': self.residual_with_costs,
        })
        return action

# =============================================================================
# [FIX] Modifikasi Wizard Pendaftaran Pembayaran
# =============================================================================
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        # Panggil metode asli terlebih dahulu
        res = super(AccountPaymentRegister, self).default_get(fields_list)
        
        # Cek konteks untuk mendapatkan tagihan aktif
        if self._context.get('active_model') == 'account.move' and self._context.get('active_ids'):
            # Ambil record tagihan
            bill = self.env['account.move'].browse(self._context.get('active_ids'))
            
            # Jika tagihan memiliki jurnal biaya tambahan
            if bill.extra_cost_journal_id:
                # Cari baris hutang dari jurnal biaya tambahan
                extra_payable_line = bill.extra_cost_journal_id.line_ids.filtered(
                    lambda line: line.account_id.internal_type == 'payable' and not line.reconciled
                )
                
                if extra_payable_line:
                    # Dapatkan ID baris hutang yang sudah ada (dari tagihan utama)
                    existing_line_ids = res.get('line_ids', [])
                    # Tambahkan ID baris hutang dari jurnal biaya tambahan
                    all_line_ids = existing_line_ids + [(4, extra_payable_line.id)]
                    res['line_ids'] = all_line_ids
                    
        return res