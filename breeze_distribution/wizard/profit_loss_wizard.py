# nama_modul/wizard/profit_loss_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import calendar
import base64
import io

class ProfitLossWizard(models.TransientModel):
    # Ganti nama modelnya
    _name = 'profit.loss.wizard'
    _description = 'Wizard untuk Laporan Laba Rugi'

    def _get_year_selection(self):
        """Membuat daftar pilihan tahun dari 2020 hingga tahun sekarang + 1."""
        current_year = date.today().year
        return [(str(y), str(y)) for y in range(2020, current_year + 2)]

    # === PILIHAN MODE UTAMA ===
    filter_type = fields.Selection([
        ('standar', 'Standar (Rentang Tanggal)'),
        ('multi', 'Multi Periode (Perbandingan)')
    ], string='Tipe Laporan', default='standar', required=True)

    # === FIELD UNTUK MODE STANDAR ===
    date_from = fields.Date(string='Dari Tanggal', default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(string='Sampai Tanggal', default=fields.Date.context_today)

    # === FIELD UNTUK MODE MULTI PERIODE ===
    multi_period_type = fields.Selection([
        ('monthly', 'Bulanan'),
        ('yearly', 'Tahunan')
    ], string='Jenis Perbandingan', default='monthly')

    # Fields untuk perbandingan bulanan
    month_from = fields.Selection([
        ('1', 'Januari'), ('2', 'Februari'), ('3', 'Maret'), ('4', 'April'),
        ('5', 'Mei'), ('6', 'Juni'), ('7', 'Juli'), ('8', 'Agustus'),
        ('9', 'September'), ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember')
    ], string='Dari Bulan', default=str(date.today().month))
    month_to = fields.Selection([
        ('1', 'Januari'), ('2', 'Februari'), ('3', 'Maret'), ('4', 'April'),
        ('5', 'Mei'), ('6', 'Juni'), ('7', 'Juli'), ('8', 'Agustus'),
        ('9', 'September'), ('10', 'Oktober'), ('11', 'November'), ('12', 'Desember')
    ], string='Sampai Bulan', default=str(date.today().month))
    year_for_month = fields.Selection(selection='_get_year_selection', string='Tahun', default=lambda self: str(date.today().year))

    # Field untuk perbandingan tahunan
    year_selection = fields.Selection(selection='_get_year_selection', string='Pilih Tahun', default=lambda self: str(date.today().year))

    excel_file = fields.Binary("Excel Report")
    excel_filename = fields.Char("Excel Filename")

    @api.constrains('month_from', 'month_to', 'filter_type', 'multi_period_type')
    def _check_month_range(self):
        """Validasi rentang bulan tidak lebih dari 3 bulan."""
        for rec in self:
            if rec.filter_type == 'multi' and rec.multi_period_type == 'monthly':
                if int(rec.month_to) < int(rec.month_from):
                    raise UserError(_('Bulan "Sampai" tidak boleh lebih awal dari bulan "Dari".'))
                if (int(rec.month_to) - int(rec.month_from)) > 2:
                    raise UserError(_('Rentang perbandingan bulan tidak boleh lebih dari 3 bulan.'))

    def action_print_report(self):
        """Fungsi ini dipanggil oleh tombol 'Cetak'."""
        data = {
            'filter_type': self.filter_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'multi_period_type': self.multi_period_type,
            'month_from': self.month_from,
            'month_to': self.month_to,
            'year_for_month': self.year_for_month,
            'year_selection': self.year_selection,
        }
        return self.env.ref('breeze_distribution.action_report_profit_loss').report_action(self, data=data)

    def action_export_excel(self):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Library "xlsxwriter" tidak tersedia. Instal dengan: pip install xlsxwriter'))

        data = {
            'filter_type': self.filter_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'multi_period_type': self.multi_period_type,
            'month_from': self.month_from,
            'month_to': self.month_to,
            'year_for_month': self.year_for_month,
            'year_selection': self.year_selection,
        }

        report_obj = self.env['report.breeze_distribution.report_profit_loss']
        result = report_obj._get_report_values(self.ids, data=data)

        company = result['company']
        report_data = result['data']
        expense_details = result['expense_details']
        column_headers = result['column_headers']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Laba Rugi')

        title_format = workbook.add_format(
            {
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'font_size': 14,
            }
        )
        subtitle_format = workbook.add_format(
            {
                'align': 'center',
                'valign': 'vcenter',
            }
        )
        header_format = workbook.add_format(
            {
                'bold': True,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#f0f0f0',
            }
        )
        text_format = workbook.add_format({'border': 1})
        currency_format = workbook.add_format({'border': 1, 'num_format': '#,##0'})
        bold_currency_format = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0'})

        periods_count = max(len(column_headers), 1)
        last_col = 1 + periods_count

        sheet.merge_range(0, 0, 0, last_col, 'LAPORAN LABA RUGI', title_format)
        sheet.merge_range(1, 0, 1, last_col, company.name or '', subtitle_format)
        if data['filter_type'] == 'standar' and data.get('date_to'):
            periode_text = 'Per %s' % data['date_to']
        else:
            periode_text = 'Multi Periode'
        sheet.merge_range(2, 0, 2, last_col, periode_text, subtitle_format)

        header_row = 4
        sheet.write(header_row, 0, 'Keterangan', header_format)
        for idx, head in enumerate(column_headers or ['Saldo']):
            sheet.write(header_row, 1 + idx, head, header_format)

        row = header_row + 1

        def write_line(label, key):
            nonlocal row
            balances = report_data[key]['balances']
            sheet.write(row, 0, label, text_format)
            for idx, val in enumerate(balances):
                sheet.write(row, 1 + idx, val, currency_format)
            row += 1

        write_line('Penjualan Usaha', 'penjualan')
        write_line('Harga Pokok Penjualan', 'hpp')

        row += 1
        write_line('Pendapatan Lain-lain', 'pendapatan_lain')

        row += 1
        sheet.write(row, 0, 'Beban Usaha', header_format)
        row += 1
        for exp in expense_details:
            sheet.write(row, 0, exp['name'], text_format)
            for idx, val in enumerate(exp['balances']):
                sheet.write(row, 1 + idx, val, currency_format)
            row += 1

        row += 1
        write_line('Beban Lain-lain', 'biaya_lain')
        write_line('Pajak', 'pajak')

        workbook.close()
        output.seek(0)

        filename = 'Laba_Rugi.xlsx'
        self.write(
            {
                'excel_file': base64.b64encode(output.read()),
                'excel_filename': filename,
            }
        )
        output.close()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=profit.loss.wizard&id=%s&field=excel_file&download=true&filename=%s'
            % (self.id, filename),
            'target': 'self',
        }
