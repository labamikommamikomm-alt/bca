# nama_modul/wizard/profit_loss_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import calendar

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
        # Arahkan ke action report yang baru
        return self.env.ref('breeze_distribution.action_report_profit_loss').report_action(self, data=data)