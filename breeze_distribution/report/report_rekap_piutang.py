from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportPiutang(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        invoice = self.env['account.move'].search([('journal_id.type', '=', 'sale'),
            ('invoice_date', '>=', data['form']['date_from']), ('invoice_date', '<=', data['form']['date_to'])])
        
        company = self.env['res.company'].sudo().search([])

        company_name = self.env.company.name
        
        

        rows = {}
        for rec in invoice:
            rows[rec.id] = {
                'tanggal_faktur': rec.invoice_date,
                'no_faktur': rec.name,
                'customer': rec.partner_id.name,
                'jumlah': rec.amount_total,
                'terbayar': rec.amount_total - rec.amount_residual,
                'sisa': rec.amount_residual,
                'wilayah': rec.partner_id.city,
                'sales': rec.team_id.name,
                'keterangan': rec.payment_state,
                'currency_id': rec.currency_id
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
          'data': data['form']
        }

        
