from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class RekapPenjualan(models.TransientModel):
    _name = 'report.rekap_penjualan'
    
    filter_type = fields.Selection([
        ('all', 'Semua'),
        ('period', 'Periode')
    ], string='Tipe Laporan', default='all', required=True)
    customer_id = fields.Many2one('res.partner',string='Pembeli')
    date_from = fields.Date(string='Dari Tanggal', default=fields.Date.context_today)
    date_to = fields.Date(string='Sampai Tanggal', default=fields.Date.context_today)

    def check_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read(['filter_type', 'customer_id', 'date_from', 'date_to'])[0]
        }
        # Pastikan baris di bawah ini lengkap, jangan cuma sampai '.r'
        return self.env.ref('breeze_distribution.report_rekap_penjualan_action').report_action(self, data=data)
    
    def export_excel(self):
        if not xlsxwriter:
            raise UserError(_("Library 'xlsxwriter' not found. Please contact your system administrator."))
            
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self.read(['filter_type', 'customer_id', 'date_from', 'date_to'])[0]
        }
        
        report_model = self.env['report.breeze_distribution.report_rekap_penjualan']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Penjualan')
        
        h_color = report_values.get('header_color', '#f2f2f2')
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': h_color, 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        bold_num_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0'})
        
        # Header
        sheet.merge_range('A1:G1', 'REKAP PENJUALAN', title_format)
        sheet.write('A3', 'Tipe Laporan:', workbook.add_format({'bold': True}))
        sheet.write('B3', 'Semua' if self.filter_type == 'all' else 'Periode')
        
        if self.filter_type == 'period':
            sheet.write('A4', 'Periode:', workbook.add_format({'bold': True}))
            sheet.write('B4', f"{self.date_from.strftime('%d/%m/%Y') if self.date_from else '-'} s/d {self.date_to.strftime('%d/%m/%Y') if self.date_to else '-'}")
            
        if self.customer_id:
            sheet.write('A5', 'Customer:', workbook.add_format({'bold': True}))
            sheet.write('B5', self.customer_id.name)
        else:
            sheet.write('A5', 'Customer:', workbook.add_format({'bold': True}))
            sheet.write('B5', 'Semua Pembeli')
            
        # Table Headers
        headers = ['No', 'Tgl Faktur', 'Nomor Faktur', 'Customer', 'Subtotal', 'PPN', 'Total']
        for col, h in enumerate(headers):
            sheet.write(7, col, h, header_format)
            
        sheet.set_column('B:C', 15)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:G', 15)
        
        row = 8
        for line in lines:
            sheet.write(row, 0, line['no'], text_center)
            sheet.write(row, 1, line['tgl_faktur'].strftime('%d/%m/%Y') if line['tgl_faktur'] else '', text_center)
            sheet.write(row, 2, line['faktur'], text_left)
            sheet.write(row, 3, line['customer'], text_left)
            sheet.write_number(row, 4, line['sub_total'], num_format)
            sheet.write_number(row, 5, line['ppn'], num_format)
            sheet.write_number(row, 6, line['total'], num_format)
            row += 1
            
        # Grand Totals
        sheet.merge_range(row, 0, row, 3, 'GRAND TOTAL', workbook.add_format({'bold': True, 'border': 1, 'align': 'center'}))
        sheet.write_number(row, 4, report_values.get('tn', 0), bold_num_format)
        sheet.write_number(row, 5, report_values.get('tp', 0), bold_num_format)
        sheet.write_number(row, 6, report_values.get('total', 0), bold_num_format)
        
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        
        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Penjualan.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
    
    def preview_report(self):
        # customer_id = 0 means All Customers
        customer_id = self.customer_id.id if self.customer_id else 0
        url = 'distribution/rekap_penjualan/preview/' + str(customer_id)
        return {
            'type' : 'ir.actions.act_url',
            'url' : url,
            'target' : '_blank'
        }