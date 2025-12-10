from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportHasilTagihan(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_hasil_tagihan'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        company = self.env['res.company'].sudo().search([])

        company_name = self.env.user.company_id.name

        sales = self.env['breeze_distribution.assign'].search([('tanggal', '>=', data['form']['date_from']),
                ('tanggal', '<=', data['form']['date_to'])])

        rows = {}
        cash = 0
        transfer = 0
        total = 0
        
        for id in sales.sales_id:
            for rec in sales:
                currency_id = False
                if rec.sales_id.id == id.id:
                    for invoice in rec.invoice_id:
                        journal = self.env['account.move'].sudo().search(
                                  [('ref', '=', invoice.name), '|', ('journal_id.type', '=', 'cash'), ('journal_id.type', '=', 'bank')])
                        for method in journal:
                            # if len(journal)
                            # raise ValidationError(str(method.total_debit))
                            if method[0].type == 'cash':
                                for debit in method[0].line_ids:
                                    cash += debit.debit
                                    currency_id = invoice.currency_id
                            elif method[0].type == 'bank':
                                for debit in method[0].line_ids:
                                    transfer += debit.debit
                                    currency_id = invoice.currency_id
                    total = cash + transfer
            rows[id.id] = {
                'sales': id.name,
                'cash': cash,
                'transfer': transfer,
                'total': total
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
          'currency_id': currency_id
        }

        
