from odoo import api, models, fields
from odoo.exceptions import UserError
from datetime import date
import calendar

class ReportRekapPiutangPerbulan(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang_perbulan'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                ("Form content is missing, this report cannot be printed."))
        
        selected_year = int(data['form']['year'])
        
        months = [
            'JANUARI', 'FEBRUARI', 'MARET', 'APRIL', 'MEI', 'JUNI',
            'JULI', 'AGUSTUS', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DESEMBER'
        ]

        # Initialize the 12 months data
        lines = []
        for i, month_name in enumerate(months):
            lines.append({
                'bulan_idx': i + 1,
                'bulan': month_name,
                'piutang': 0.0,
                'terbayar': 0.0,
                'sisa': 0.0,
            })

        company = self.env.company
        currency_id = company.currency_id

        # Fetch all sales invoices for the year
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)

        invoices = self.env['account.move'].search([
            ('journal_id.type', '=', 'sale'),
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])

        # Aggregate data by month
        for inv in invoices:
            if not inv.invoice_date:
                continue
            
            month_idx = inv.invoice_date.month - 1
            
            # Add to the specific month
            lines[month_idx]['piutang'] += inv.amount_total
            lines[month_idx]['sisa'] += inv.amount_residual
            lines[month_idx]['terbayar'] += (inv.amount_total - inv.amount_residual)

        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company.name,
          'year': str(selected_year),
          'currency_id': currency_id,
        }
