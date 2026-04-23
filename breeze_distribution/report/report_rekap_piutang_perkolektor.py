from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
import json


class ReportPiutangPerkolektor(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang_perkolektor'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model') or 'report.rekap_piutang_perkolektor'
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])

        company = self.env.user.company_id
        company_name = company.name
        currency_id = company.currency_id

        # Search for all open or partially paid customer invoices
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', data['form']['date_from']),
            ('invoice_date', '<=', data['form']['date_to']),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ]
        
        invoices = self.env['account.move'].sudo().search(domain)
        
        # Group by Kolektor (Sales Team)
        rows = {}
        grand_total_piutang = 0.0
        grand_total_terbayar = 0.0
        grand_total_sisa = 0.0
        
        for inv in invoices:
            col_id = inv.team_id.id or 0
            if col_id not in rows:
                rows[col_id] = {
                    'sales': inv.team_id.name or _('No Kolektor'),
                    'piutang': 0.0,
                    'terbayar': 0.0,
                    'sisa': 0.0,
                }
            rows[col_id]['piutang'] += inv.amount_total
            rows[col_id]['sisa'] += inv.amount_residual
            rows[col_id]['terbayar'] += (inv.amount_total - inv.amount_residual)
            
            grand_total_piutang += inv.amount_total
            grand_total_sisa += inv.amount_residual
            grand_total_terbayar += (inv.amount_total - inv.amount_residual)

        lines = list(rows.values())

        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'currency_id': currency_id,
          'total_piutang': grand_total_piutang,
          'total_terbayar': grand_total_terbayar,
          'total_sisa': grand_total_sisa,
        }

        
