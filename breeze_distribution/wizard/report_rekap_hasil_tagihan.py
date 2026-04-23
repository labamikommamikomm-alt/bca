from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class RekapHasilTagihan(models.TransientModel):
    _name = 'report.rekap_hasil_tagihan'

    date_from = fields.Date(string="Starting Date")
    date_to = fields.Date(string="Ending Date")


    def _build_comparison_context(self, data):
        result = {}
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['date_from', 'date_to'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        # raise ValidationError(data['form']['from_date'])
        return self.env.ref('breeze_distribution.report_rekap_hasil_tagihan_action').report_action(self, data=data)

    def export_excel(self):
        if not xlsxwriter:
            raise UserError(_("Library 'xlsxwriter' not found. Please contact your system administrator."))
            
        self.ensure_one()
        data = {}
        data['form'] = self.read(['date_from', 'date_to'])[0]
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        
        report_model = self.env['report.breeze_distribution.report_rekap_hasil_tagihan']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Hasil Tagihan')
        
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#b3cefc', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        bold_num_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0'})
        
        # Header
        sheet.merge_range('A1:E1', 'REKAP HASIL TAGIHAN', title_format)
        sheet.write('A3', 'Periode:', workbook.add_format({'bold': True}))
        sheet.write('B3', f"{self.date_from.strftime('%d/%m/%Y') if self.date_from else '-'} s/d {self.date_to.strftime('%d/%m/%Y') if self.date_to else '-'}")
        
        # Table Headers
        headers = ['No', 'Nama Sales', 'Cash', 'Transfer', 'Total']
        for col, h in enumerate(headers):
            sheet.write(5, col, h, header_format)
            
        sheet.set_column('B:B', 30)
        sheet.set_column('C:E', 20)
        
        row = 6
        for idx, line in enumerate(lines):
            sheet.write(row, 0, idx + 1, text_center)
            sheet.write(row, 1, line.get('sales', ''), text_left)
            sheet.write_number(row, 2, line.get('cash', 0.0), num_format)
            sheet.write_number(row, 3, line.get('transfer', 0.0), num_format)
            sheet.write_number(row, 4, line.get('total', 0.0), num_format)
            row += 1
            
        # Grand Totals
        sheet.merge_range(row, 0, row, 1, 'GRAND TOTAL', workbook.add_format({'bold': True, 'border': 1, 'align': 'center'}))
        sheet.write_number(row, 2, report_values.get('total_cash', 0), bold_num_format)
        sheet.write_number(row, 3, report_values.get('total_transfer', 0), bold_num_format)
        sheet.write_number(row, 4, report_values.get('total_total', 0), bold_num_format)
        
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        
        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Hasil_Tagihan.xlsx',
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