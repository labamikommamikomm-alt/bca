from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportHutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_hutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                ("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        invoice = self.env['account.move'].search([('journal_id.type', '=', 'purchase'),
            ('payment_state', '=', 'not_paid'), ('invoice_date', '>=', data['form']['date_from']), ('invoice_date', '<=', data['form']['date_to'])])
        
        company = self.env['res.company'].sudo().search([])

        company = self.env.user.company_id
        
        company_name = company.name

        rows = {}
        total = 0
        total_ppn = 0
        currency_id = False
        for rec in invoice:
            currency_id = rec.currency_id
            total += rec.amount_total 
            total_ppn += rec.amount_tax
            rows[rec.id] = {
                'tanggal_faktur': rec.invoice_date,
                'no_faktur': rec.name,
                'customer': rec.partner_id.name,
                'ppn': rec.amount_tax,
                'jumlah': rec.amount_total,
            }
        lines = []
        
        for i in rows:
            lines.append(rows[i])

        if total_ppn == False:
            total_ppn = 0
        # raise ValidationError(json.dumps(lines))
        return {
          'lines': lines,
          'total': total,
          'total_ppn': total_ppn,
          'company_name': company_name,
          'doc_ids': docids,
          'docs': docs,
          'currency_id': self.env.user.currency_id  ,
          'data': data['form']
        }

        
