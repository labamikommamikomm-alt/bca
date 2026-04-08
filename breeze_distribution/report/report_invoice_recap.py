from odoo import api, models, fields
from odoo.exceptions import UserError
import datetime

class ReportInvoiceRecap(models.AbstractModel):
    _name = 'report.breeze_distribution.report_invoice_recap'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data or not data.get('form') or not data['form'].get('invoice_ids'):
            raise UserError("Form content atau data invoice is missing, this report cannot be printed.")
            
        form_data = data['form']
        invoice_ids = form_data.get('invoice_ids', [])
        
        invoices = self.env['account.move'].browse(invoice_ids)
        sorted_invoices = invoices.sorted(key=lambda x: (x.invoice_date or fields.Date.today(), x.name or ''))

        lines = []
        for inv in sorted_invoices:
            payment_state_dict = dict(inv._fields['payment_state'].selection)
            state_dict = dict(inv._fields['state'].selection)
            
            p_state = payment_state_dict.get(inv.payment_state, inv.payment_state) if inv.payment_state else ''
            i_state = state_dict.get(inv.state, inv.state) if inv.state else ''
            
            sales_name = inv.invoice_user_id.name if inv.invoice_user_id else (inv.team_id.name if inv.team_id else '')
            
            lines.append({
                'tanggal_faktur': inv.invoice_date,
                'no_faktur': inv.name or '',
                'customer': inv.partner_id.name or '',
                'wilayah': inv.partner_id.city or '',
                'sales': sales_name,
                'total_tagihan': inv.amount_total,
                'sisa_tagihan': inv.amount_residual,
                'payment_state': p_state,
                'state': i_state,
                'currency_id': inv.currency_id,
            })

        company = self.env.company

        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company.name,
          'data': form_data,
        }
