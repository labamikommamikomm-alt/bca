from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportPembayaranHutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_pembayaran_hutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        invoice = self.env['account.move'].search([('journal_id.type', '=', 'purchase'), ('payment_state', '=', 'paid'),
            ('invoice_date', '>=', data['form']['date_from']), ('invoice_date', '<=', data['form']['date_to'])])

        company = self.env['res.company'].sudo().search([])

        company_name = self.env.company.name

        rows = {}
        total = 0
        currency_id = False
        for rec in invoice:
            journal = self.env['account.move'].sudo().search(
            [('ref', '=', rec.name), '|', ('journal_id.type', '=', 'cash'), ('journal_id.type', '=', 'bank')])
            tanggal = []
            jenis = []
            # raise ValidationError(json.dumps(rec.name))
            for record in journal:
                tanggal.append(record.date)
            for record in journal:
                jenis.append(record.journal_id.name)
            currency_id = rec.currency_id
            total += rec.amount_total 
            rows[rec.id] = {
                'tanggal_faktur': rec.invoice_date,
                'no_faktur': rec.name,
                'customer': rec.partner_id.name,
                'jumlah': rec.amount_total,
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
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'currency_id': currency_id,
          'data': data['form']
        }

        
