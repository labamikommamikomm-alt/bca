from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
from datetime import date
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class RekapPiutangPerbulan(models.TransientModel):
    _name = 'report.rekap_piutang_perbulan'
    _description = 'Wizard Rekap Piutang Perbulan'

    # Generate year selection dynamically
    def _get_years(self):
        current_year = date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    year = fields.Selection(selection='_get_years', string="Tahun", default=lambda s: str(date.today().year), required=True)

    def check_report(self):
        data = {'form': self.read(['year'])[0]}
        return self.env.ref('breeze_distribution.report_rekap_piutang_perbulan_action').report_action(self, data=data)

    def export_excel(self):
        data = {'form': self.read(['year'])[0]}
        report_model = self.env['report.breeze_distribution.report_rekap_piutang_perbulan']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Piutang Perbulan')

        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        year_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        subtotal_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0'})
        subtotal_label = workbook.add_format({'bold': True, 'border': 1, 'align': 'left'})

        company_name = report_values.get('company_name', '')
        selected_year = report_values.get('year', '')

        sheet.merge_range('A1:D1', company_name, title_format)
        sheet.merge_range('A2:D2', selected_year, year_format)

        headers = ['BULAN', 'TOTAL', 'TERBAYAR', 'SISA']
        for col, h in enumerate(headers):
            sheet.write(4, col, h, header_format)
            
        sheet.set_column('A:A', 20)
        sheet.set_column('B:D', 25)

        row = 5
        tot_piutang = 0
        tot_terbayar = 0
        tot_sisa = 0

        for m in lines:
            piutang = m['piutang']
            terbayar = m['terbayar']
            sisa = m['sisa']

            sheet.write(row, 0, m['bulan'], text_left)
            sheet.write_number(row, 1, piutang, num_format)
            sheet.write_number(row, 2, terbayar, num_format)
            sheet.write_number(row, 3, sisa, num_format)

            tot_piutang += piutang
            tot_terbayar += terbayar
            tot_sisa += sisa
            row += 1

        sheet.write(row, 0, 'TOTAL', subtotal_label)
        sheet.write_number(row, 1, tot_piutang, subtotal_format)
        sheet.write_number(row, 2, tot_terbayar, subtotal_format)
        sheet.write_number(row, 3, tot_sisa, subtotal_format)

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'Rekap_Piutang_Perbulan_{selected_year}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'report.rekap_piutang_perbulan',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
