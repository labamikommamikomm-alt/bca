from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
from datetime import date
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class RekapPiutangPersales(models.TransientModel):
    _name = 'report.rekap_piutang_persales'
    _description = 'Wizard Rekap Piutang Persales'

    judul = fields.Char(string="Judul Laporan", default="REKAPITULASI PIUTANG PER SALES")
    date_from = fields.Date(string="Dari Tanggal")
    date_to = fields.Date(string="Sampai Tanggal")
    
    def _get_years(self):
        current_year = date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    bulan_selection = fields.Selection([
        ('1', 'Januari'), ('2', 'Februari'), ('3', 'Maret'), ('4', 'April'),
        ('5', 'Mei'), ('6', 'Juni'), ('7', 'Juli'), ('8', 'Agustus'),
        ('9', 'September'), ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember')
    ], string="Bulan")
    
    tahun_selection = fields.Selection(selection='_get_years', string="Tahun")
    
    team_id = fields.Many2one('crm.team', string="Sales Team / Kolektor")

    def check_report(self):
        data = {'form': self.read(['judul', 'date_from', 'date_to', 'bulan_selection', 'tahun_selection', 'team_id'])[0]}
        if data['form']['team_id']:
            data['form']['team_id'] = data['form']['team_id'][0]
            
        return self.env.ref('breeze_distribution.report_rekap_piutang_persales_action').report_action(self, data=data)

    def export_excel(self):
        data = {'form': self.read(['judul', 'date_from', 'date_to', 'bulan_selection', 'tahun_selection', 'team_id'])[0]}
        if data['form']['team_id']:
            data['form']['team_id'] = data['form']['team_id'][0]
            
        report_model = self.env['report.breeze_distribution.report_rekap_piutang_persales']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Piutang Persales')

        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        filter_bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        subtotal_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0'})

        judul_report = data['form'].get('judul') or 'REKAPITULASI PIUTANG PER SALES'
        sheet.merge_range('A1:G1', judul_report, title_format)

        sheet.write('A3', 'Dari Tanggal:', filter_bold)
        sheet.write('B3', str(data['form']['date_from'] or '-'))
        sheet.write('A4', 'Sampai Tanggal:', filter_bold)
        sheet.write('B4', str(data['form']['date_to'] or '-'))
        sheet.write('A5', 'Periode Bulan/Tahun:', filter_bold)
        sheet.write('B5', f"{dict(self._fields['bulan_selection'].selection).get(data['form']['bulan_selection'], '-')} / {data['form']['tahun_selection'] or '-'}")
        sheet.write('A6', 'Sales Team:', filter_bold)
        sheet.write('B6', self.team_id.name if self.team_id else 'Semua Sales Team')

        headers = ['No', 'Tanggal Faktur', 'No Faktur', 'Customer', 'Piutang', 'Terbayar', 'Sisa']
        for col, h in enumerate(headers):
            sheet.write(8, col, h, header_format)
            
        sheet.set_column('A:A', 5)
        sheet.set_column('B:C', 15)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:G', 20)

        row = 9
        idx = 1
        tot_piutang = 0
        tot_terbayar = 0
        tot_sisa = 0

        for line in lines:
            piutang = line.get('jumlah', 0)
            terbayar = line.get('terbayar', 0)
            sisa = line.get('sisa', 0)

            sheet.write(row, 0, idx, text_center)
            sheet.write(row, 1, line.get('tanggal_faktur', '').strftime('%d/%m/%Y') if hasattr(line.get('tanggal_faktur'), 'strftime') else '', text_center)
            sheet.write(row, 2, line.get('no_faktur', ''), text_left)
            sheet.write(row, 3, line.get('customer', ''), text_left)
            sheet.write_number(row, 4, piutang, num_format)
            sheet.write_number(row, 5, terbayar, num_format)
            sheet.write_number(row, 6, sisa, num_format)
            
            tot_piutang += piutang
            tot_terbayar += terbayar
            tot_sisa += sisa
            idx += 1
            row += 1

        sheet.merge_range(row, 0, row, 3, 'TOTAL', workbook.add_format({'bold': True, 'border': 1, 'align': 'center'}))
        sheet.write_number(row, 4, tot_piutang, subtotal_format)
        sheet.write_number(row, 5, tot_terbayar, subtotal_format)
        sheet.write_number(row, 6, tot_sisa, subtotal_format)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Piutang_Persales.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'report.rekap_piutang_persales',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
