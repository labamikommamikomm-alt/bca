from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
import json


class ReportPembayaranHutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_pembayaran_hutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model') or 'report.rekap_pembayaran_hutang'
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        invoice = self.env['account.move'].search([('journal_id.type', '=', 'purchase'), ('payment_state', '=', 'paid'),
            ('invoice_date', '>=', data['form']['date_from']), ('invoice_date', '<=', data['form']['date_to'])])

        company = self.env['res.company'].sudo().search([])

        company_name = self.env.company.name

        rows = {}
        total = 0
        total_ppn = 0
        total_pph = 0
        total_admin = 0
        currency_id = False
        for rec in invoice:
            # Find reconciled payments through move lines
            # Reconciled lines are those reconciled with the payable account lines of the move (Vendor Bills)
            pay_lines = rec.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'payable')
            reconciled_moves = pay_lines.mapped('matched_debit_ids.debit_move_id.move_id') | \
                               pay_lines.mapped('matched_credit_ids.credit_move_id.move_id')
            
            # Filter for cash/bank journals
            valid_payments = reconciled_moves.filtered(lambda m: m.journal_id.type in ('bank', 'cash'))
            
            tanggal = []
            jenis = []
            
            for p in valid_payments:
                if p.date:
                    tanggal.append(p.date)
                jenis.append(p.journal_id.name)
            
            # Global Taxes
            global_taxes = rec.global_tax_ids
            ppn_val = sum(global_taxes.filtered(lambda t: 'PPN' in t.global_tax_id.name).mapped('amount'))
            pph_val = sum(global_taxes.filtered(lambda t: 'PPh' in t.global_tax_id.name).mapped('amount'))
            admin_val = sum(global_taxes.filtered(lambda t: 'Admin' in t.global_tax_id.name).mapped('amount'))

            currency_id = rec.currency_id
            total += rec.amount_total 
            total_ppn += ppn_val
            total_pph += pph_val
            total_admin += admin_val

            rows[rec.id] = {
                'tanggal_faktur': rec.invoice_date,
                'no_faktur': rec.name,
                'customer': rec.partner_id.name,
                'jumlah': rec.amount_total,
                'ppn': ppn_val,
                'pph': pph_val,
                'admin': admin_val,
                'jenis_pembayaran': jenis,
                'tanggal_bayar': tanggal
            }
        lines = []
        
        for i in rows:
            lines.append(rows[i])

        # raise ValidationError(json.dumps(lines))
        return {
          'lines': lines,
          'total': total,
          'total_ppn': total_ppn,
          'total_pph': total_pph,
          'total_admin': total_admin,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'currency_id': currency_id,
          'data': data['form']
        }

        
