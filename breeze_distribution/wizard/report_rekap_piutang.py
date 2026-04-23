from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class RekapPiutang(models.TransientModel):
    _name = 'report.rekap_piutang'

    date_from = fields.Date(string="Starting Date")
    date_to = fields.Date(string="Ending Date")
    team_id = fields.Many2one('crm.team', string="Sales Team / Kolektor")
    partner_id = fields.Many2one('res.partner', string="Customer")
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('in_payment', 'In Payment'),
        ('all', 'Semua (All)')
    ], string="Status Pembayaran", default='all')

    def _build_comparison_context(self, data):
        result = {}
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['date_from', 'date_to', 'team_id', 'partner_id', 'payment_state'])[0]
        
        if data['form']['team_id']:
            data['form']['team_id'] = data['form']['team_id'][0]
        if data['form']['partner_id']:
            data['form']['partner_id'] = data['form']['partner_id'][0]
            
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref('breeze_distribution.report_rekap_piutang_action').report_action(self, data=data)

    def export_excel(self):
        data = {}
        data['form'] = self.read(['date_from', 'date_to', 'team_id', 'partner_id', 'payment_state'])[0]
        if data['form']['team_id']:
            data['form']['team_id'] = data['form']['team_id'][0]
        if data['form']['partner_id']:
            data['form']['partner_id'] = data['form']['partner_id'][0]

        report_model = self.env['report.breeze_distribution.report_rekap_piutang']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Piutang')

        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#b3cefc', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})

        sheet.merge_range('A1:J1', 'LAPORAN REKAP PIUTANG', title_format)

        sheet.write('A3', 'Tipe Filter', workbook.add_format({'bold': True}))
        sheet.write('A4', f"Tanggal: {data['form']['date_from'] or '-'} to {data['form']['date_to'] or '-'}")
        team_name = report_values.get('data', {}).get('team_name', 'Semua')
        partner_name = report_values.get('data', {}).get('partner_name', 'Semua')
        sheet.write('A5', f"Sales Team / Kolektor: {team_name}")
        sheet.write('A6', f"Customer: {partner_name}")
        
        headers = ['No', 'Tanggal Jual', 'Nota Penjualan', 'Customer', 'Piutang', 'Terbayar', 'Sisa Piutang', 'Sales', 'Kota', 'Keterangan']
        for col, h in enumerate(headers):
            sheet.write(7, col, h, header_format)
            
        sheet.set_column('B:C', 15)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:G', 15)
        sheet.set_column('H:J', 20)

        row = 8
        idx = 1
        for line in lines:
            sheet.write(row, 0, idx, text_center)
            sheet.write(row, 1, line.get('tanggal_faktur', '').strftime('%d/%m/%Y ') if hasattr(line.get('tanggal_faktur'), 'strftime') else '', text_center)
            sheet.write(row, 2, line.get('no_faktur', ''), text_left)
            sheet.write(row, 3, line.get('customer', ''), text_left)
            sheet.write_number(row, 4, line.get('jumlah', 0), num_format)
            sheet.write_number(row, 5, line.get('terbayar', 0), num_format)
            sheet.write_number(row, 6, line.get('sisa', 0), num_format)
            sheet.write(row, 7, line.get('sales', ''), text_left)
            sheet.write(row, 8, line.get('wilayah', ''), text_left)
            sheet.write(row, 9, line.get('keterangan', ''), text_left)
            
            idx += 1
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Piutang.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'report.rekap_piutang',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }