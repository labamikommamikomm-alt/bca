from odoo import models, fields, api
import json

class AccountMove(models.Model):
    _inherit = 'account.move'

    last_payment_date = fields.Date(string='Tanggal Pembayaran', compute='_compute_last_payment_info', store=True)
    last_payment_method_name = fields.Char(string='Metode Pembayaran', compute='_compute_last_payment_info', store=True)

    @api.depends('invoice_payments_widget')
    def _compute_last_payment_info(self):
        for move in self:
            last_date = False
            last_method = ""
            if move.invoice_payments_widget and move.invoice_payments_widget != 'false':
                try:
                    payments = json.loads(move.invoice_payments_widget)
                    if payments and 'content' in payments and len(payments['content']) > 0:
                        # Assuming the content list is ordered, or we take the last one naturally
                        # You could also sort by payments['content'][i]['date'] to be entirely sure
                        latest_payment = max(payments['content'], key=lambda x: x.get('date', ''))
                        last_date = latest_payment.get('date')
                        last_method = latest_payment.get('journal_name')
                except Exception as e:
                    pass
            move.last_payment_date = last_date
            move.last_payment_method_name = last_method
