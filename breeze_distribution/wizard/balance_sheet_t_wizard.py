# nama_modul/wizard/balance_sheet_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import calendar
import base64
import io


class BalanceSheetTWizard(models.TransientModel):
    _name = "balance.sheet.t.wizard"
    _description = "Wizard untuk Laporan Neraca T"

    def _get_year_selection(self):
        """Membuat daftar pilihan tahun dari 2020 hingga tahun sekarang + 1."""
        current_year = date.today().year
        return [(str(y), str(y)) for y in range(2020, current_year + 2)]

    # === PILIHAN MODE UTAMA ===
    filter_type = fields.Selection(
        [
            ("standar", "Standar (Rentang Tanggal)"),
            ("multi", "Multi Periode (Perbandingan)"),
        ],
        string="Tipe Laporan",
        default="standar",
        required=True,
    )

    # === FIELD UNTUK MODE STANDAR ===
    date_from = fields.Date(
        string="Dari Tanggal", default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(string="Sampai Tanggal", default=fields.Date.context_today)

    # === FIELD UNTUK MODE MULTI PERIODE ===
    multi_period_type = fields.Selection(
        [("monthly", "Bulanan"), ("yearly", "Tahunan")],
        string="Jenis Perbandingan",
        default="monthly",
    )

    # Fields untuk perbandingan bulanan
    month_from = fields.Selection(
        [
            ("1", "Januari"),
            ("2", "Februari"),
            ("3", "Maret"),
            ("4", "April"),
            ("5", "Mei"),
            ("6", "Juni"),
            ("7", "Juli"),
            ("8", "Agustus"),
            ("9", "September"),
            ("10", "Oktober"),
            ("11", "November"),
            ("12", "Desember"),
        ],
        string="Dari Bulan",
        default=str(date.today().month),
    )
    month_to = fields.Selection(
        [
            ("1", "Januari"),
            ("2", "Februari"),
            ("3", "Maret"),
            ("4", "April"),
            ("5", "Mei"),
            ("6", "Juni"),
            ("7", "Juli"),
            ("8", "Agustus"),
            ("9", "September"),
            ("10", "Oktober"),
            ("11", "November"),
            ("12", "Desember"),
        ],
        string="Sampai Bulan",
        default=str(date.today().month),
    )
    year_for_month = fields.Selection(
        selection="_get_year_selection",
        string="Tahun",
        default=lambda self: str(date.today().year),
    )

    # Field untuk perbandingan tahunan
    year_selection = fields.Selection(
        selection="_get_year_selection",
        string="Pilih Tahun",
        default=lambda self: str(date.today().year),
    )

    excel_file = fields.Binary("Excel Report")
    excel_filename = fields.Char("Excel Filename")

    @api.constrains("month_from", "month_to", "filter_type", "multi_period_type")
    def _check_month_range(self):
        """Validasi rentang bulan tidak lebih dari 3 bulan."""
        for rec in self:
            if rec.filter_type == "multi" and rec.multi_period_type == "monthly":
                if int(rec.month_to) < int(rec.month_from):
                    raise UserError(
                        _('Bulan "Sampai" tidak boleh lebih awal dari bulan "Dari".')
                    )
                if (int(rec.month_to) - int(rec.month_from)) > 2:
                    raise UserError(
                        _("Rentang perbandingan bulan tidak boleh lebih dari 3 bulan.")
                    )

    def action_print_report(self):
        """Fungsi ini dipanggil oleh tombol 'Cetak'."""
        data = {
            "filter_type": self.filter_type,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "multi_period_type": self.multi_period_type,
            "month_from": self.month_from,
            "month_to": self.month_to,
            "year_for_month": self.year_for_month,
            "year_selection": self.year_selection,
        }
        return self.env.ref(
            "breeze_distribution.action_report_balance_sheet_t"
        ).report_action(self, data=data)

    def action_export_excel(self):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                _(
                    'Library "xlsxwriter" tidak tersedia. Instal dengan: pip install xlsxwriter'
                )
            )

        data = {
            "filter_type": self.filter_type,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "multi_period_type": self.multi_period_type,
            "month_from": self.month_from,
            "month_to": self.month_to,
            "year_for_month": self.year_for_month,
            "year_selection": self.year_selection,
        }

        report_obj = self.env["report.breeze_distribution.report_balance_sheet_t"]
        result = report_obj._get_report_values(self.ids, data=data)

        company = result["company"]
        column_headers = result["column_headers"]
        report_data = result["data"]
        total_assets = result["total_assets_per_period"]
        total_le = result["total_liabilities_equity_per_period"]
        is_multi = result["is_multi_period"]
        date_to = result["date_to"]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Neraca T")

        title_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "font_size": 14,
            }
        )
        subtitle_format = workbook.add_format(
            {
                "align": "center",
                "valign": "vcenter",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#f0f0f0",
            }
        )
        text_format = workbook.add_format({"border": 1})
        currency_format = workbook.add_format({"border": 1, "num_format": "#,##0"})
        bold_currency_format = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0"}
        )

        periods_count = max(len(column_headers), 1)
        last_col = 1 + periods_count

        sheet.merge_range(0, 0, 0, last_col, "NERACA (FORMAT T)", title_format)
        sheet.merge_range(1, 0, 1, last_col, company.name or "", subtitle_format)
        if is_multi:
            periode_text = "Multi Periode"
        else:
            periode_text = "Per %s" % (date_to or "")
        sheet.merge_range(2, 0, 2, last_col, periode_text, subtitle_format)

        header_row = 4
        sheet.write(header_row, 0, "Kelompok/Akun", header_format)
        for idx, head in enumerate(column_headers or ["Saldo"]):
            sheet.write(header_row, 1 + idx, head, header_format)

        row = header_row + 1

        def write_section(title, section_key):
            nonlocal row
            section = report_data[section_key]
            sheet.write(row, 0, title, header_format)
            row += 1
            for line in section["lines"]:
                sheet.write(row, 0, line["name"], text_format)
                for idx, bal in enumerate(line["balances"]):
                    sheet.write(row, 1 + idx, bal, currency_format)
                row += 1
            sheet.write(row, 0, "TOTAL %s" % title.upper(), header_format)
            for idx, sub in enumerate(section["subtotals"]):
                sheet.write(row, 1 + idx, sub, bold_currency_format)
            row += 2

        write_section("AKTIVA LANCAR", "aktiva_lancar")
        write_section("AKTIVA TETAP", "aktiva_tetap")
        write_section("HUTANG LANCAR", "hutang_lancar")
        write_section("HUTANG JANGKA PANJANG", "hutang_jangka_panjang")
        write_section("MODAL", "modal")

        sheet.write(row, 0, "TOTAL AKTIVA", header_format)
        for idx, val in enumerate(total_assets):
            sheet.write(row, 1 + idx, val, bold_currency_format)
        row += 1
        sheet.write(row, 0, "TOTAL PASIVA", header_format)
        for idx, val in enumerate(total_le):
            sheet.write(row, 1 + idx, val, bold_currency_format)

        workbook.close()
        output.seek(0)

        filename = "Neraca_T.xlsx"
        self.write(
            {
                "excel_file": base64.b64encode(output.read()),
                "excel_filename": filename,
            }
        )
        output.close()

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/?model=balance.sheet.t.wizard&id=%s&field=excel_file&download=true&filename=%s"
            % (self.id, filename),
            "target": "self",
        }
