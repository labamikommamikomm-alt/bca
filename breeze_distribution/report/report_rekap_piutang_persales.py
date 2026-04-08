from odoo import api, models, fields
from odoo.exceptions import UserError
from datetime import date
import calendar

class ReportRekapPiutangPersales(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_piutang_persales'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                ("Form content is missing, this report cannot be printed."))
        
        form_data = data['form']

        domain = [
            ('journal_id.type', '=', 'sale'),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ]

        if form_data.get('date_from'):
            domain.append(('invoice_date', '>=', form_data['date_from']))
        if form_data.get('date_to'):
            domain.append(('invoice_date', '<=', form_data['date_to']))
            
        if form_data.get('bulan_selection') and form_data.get('tahun_selection'):
            try:
                year = int(form_data['tahun_selection'])
                month = int(form_data['bulan_selection'])
                start_date = date(year, month, 1)
                end_date = date(year, month, calendar.monthrange(year, month)[1])
                domain.append(('invoice_date', '>=', start_date))
                domain.append(('invoice_date', '<=', end_date))
            except Exception:
                pass
                
        if form_data.get('sales_id'):
            domain.append(('invoice_user_id', '=', form_data['sales_id']))

        invoices = self.env['account.move'].search(domain)
        
        company = self.env.company
        currency_id = company.currency_id

        lines = []
        for inv in invoices:
            lines.append({
                'tanggal_faktur': inv.invoice_date,
                'no_faktur': inv.name,
                'customer': inv.partner_id.name,
                'jumlah': inv.amount_total,
                'terbayar': inv.amount_total - inv.amount_residual,
                'sisa': inv.amount_residual,
            })

        # Ensure correct formatting for bulan_selection label
        bulan_map = {
            '1': 'Januari', '2': 'Februari', '3': 'Maret', '4': 'April',
            '5': 'Mei', '6': 'Juni', '7': 'Juli', '8': 'Agustus',
            '9': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
        }
        bulan_label = bulan_map.get(form_data.get('bulan_selection'), '-')

        sales_name = "Semua Sales"
        if form_data.get('sales_id'):
            sales_user = self.env['res.users'].browse(form_data['sales_id'])
            if sales_user.exists():
                sales_name = sales_user.name

        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company.name,
          'data': form_data,
          'bulan_label': bulan_label,
          'sales_name': sales_name,
          'currency_id': currency_id,
        }
