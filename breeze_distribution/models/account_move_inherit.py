from odoo import models, fields, api
import json

class AccountMove(models.Model):
    _inherit = 'account.move'

    last_payment_date = fields.Date(string='Tanggal Pembayaran', compute='_compute_last_payment_info', store=True)
    last_payment_method_name = fields.Char(string='Metode Pembayaran', compute='_compute_last_payment_info', store=True)

    @api.depends('payment_state', 'line_ids.matched_debit_ids', 'line_ids.matched_credit_ids')
    def _compute_last_payment_info(self):
        for move in self:
            # Reconciled lines are those reconciled with relevant account lines of the move
            account_type = 'receivable' if move.move_type in ('out_invoice', 'out_refund') else 'payable'
            pay_lines = move.line_ids.filtered(lambda l: l.account_id.user_type_id.type == account_type)
            reconciled_moves = pay_lines.mapped('matched_debit_ids.debit_move_id.move_id') | \
                               pay_lines.mapped('matched_credit_ids.credit_move_id.move_id')
            
            # Filter for cash/bank journals
            valid_payments = reconciled_moves.filtered(lambda m: m.journal_id.type in ('bank', 'cash')).sorted('date')
            
            if valid_payments:
                latest_payment = valid_payments[-1]
                move.last_payment_date = latest_payment.date
                move.last_payment_method_name = latest_payment.journal_id.name
            else:
                move.last_payment_date = False
                move.last_payment_method_name = ""
