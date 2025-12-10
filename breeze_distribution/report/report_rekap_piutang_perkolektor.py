from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportPiutangPerkolektor(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang_perkolektor'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                ("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        sales = self.env['breeze_distribution.assign'].search([('tanggal', '>=', data['form']['date_from']),
                ('tanggal', '<=', data['form']['date_to'])])
        
        company = self.env.user.company_id

        company_name = company.name

        rows = {}
        
        for rec in sales:
            piutang = 0
            terbayar = 0
            sisa = 0
            currency_id = False
            for invoice in rec.invoice_id:
                piutang += invoice.amount_total
                sisa += invoice.amount_residual
                terbayar = piutang - sisa
                currency_id = invoice.currency_id
            rows[rec.id] = {
                'sales': rec.sales_id.name,
                'piutang': piutang,
                'terbayar': terbayar,
                'sisa': sisa
            }
        lines = []
        
        for i in rows:
            lines.append(rows[i])

        # raise ValidationError(json.dumps(lines))
        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'currency_id': currency_id,
        }

        
