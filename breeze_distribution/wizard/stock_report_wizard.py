from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io


class StockReportWizard(models.TransientModel):
    _name = "stock.report.wizard"
    _description = "Stock Report Wizard"

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    # Field untuk nampung file excel sementara biar bisa didownload
    excel_file = fields.Binary("Excel Report")
    excel_filename = fields.Char("Excel Filename")

    def print_stock_report(self):
        data = {
            "start_date": self.start_date,
            "end_date": self.end_date,
        }
        return self.env.ref(
            "breeze_distribution.action_report_stock_by_period"
        ).report_action(self, data=data)

    def action_print_excel(self):
        # 1. SIAPKAN LOGIKA DATA (SAMA PERSIS DENGAN PDF)
        start_date = self.start_date
        end_date = self.end_date
        products = self.env["product.product"].search([("active", "=", True)])

        # --- Logic SO Awal ---
        so_awal_products = {}
        last_inventories = self.env["stock.inventory"].search(
            [
                ("state", "=", "done"),
                ("accounting_date", "<", start_date),
            ],
            order="accounting_date desc, date desc",
        )

        processed_products_so_awal = set()
        for inv in last_inventories:
            for line in inv.line_ids:
                if line.product_id.id not in processed_products_so_awal:
                    so_awal_products[line.product_id.id] = line.product_qty
                    processed_products_so_awal.add(line.product_id.id)
            if len(processed_products_so_awal) == len(products):
                break

        # --- Logic Moves (IN/OUT) ---
        moves = self.env["stock.move"].search(
            [
                ("product_id", "in", products.ids),
                ("state", "=", "done"),
                ("date", ">=", start_date),
                ("date", "<=", end_date),
            ]
        )
        move_data = {prod.id: {"in_qty": 0, "out_qty": 0} for prod in products}
        for move in moves:
            pid = move.product_id.id
            qty = move.product_uom_qty
            if (
                move.location_dest_id.usage == "internal"
                and move.location_id.usage != "internal"
            ):
                move_data[pid]["in_qty"] += qty
            elif (
                move.location_id.usage == "internal"
                and move.location_dest_id.usage != "internal"
            ):
                move_data[pid]["out_qty"] += qty

        # --- Logic SO Fisik ---
        so_fisik_products = {}
        opnames_in_period = self.env["stock.inventory"].search(
            [
                ("state", "=", "done"),
                ("accounting_date", ">=", start_date),
                ("accounting_date", "<=", end_date),
            ],
            order="accounting_date asc, date asc",
        )

        for opname in opnames_in_period:
            for line in opname.line_ids:
                so_fisik_products[line.product_id.id] = line.product_qty

        # 2. MULAI BIKIN EXCEL
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                _(
                    "Module xlsxwriter not found. Please install it using 'pip install xlsxwriter'"
                )
            )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Stock Opname")

        header_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "bg_color": "#f0f0f0",
            }
        )
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
        text_format = workbook.add_format({"border": 1})
        num_format = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        currency_format = workbook.add_format({"border": 1, "num_format": "#,##0"})
        bold_currency_format = workbook.add_format(
            {"bold": True, "border": 1, "num_format": "#,##0"}
        )
        red_currency_format = workbook.add_format(
            {"border": 1, "num_format": "#,##0", "font_color": "red"}
        )

        headers = [
            "NO",
            "NAMA BARANG",
            "SATUAN",
            "SO AWAL",
            "IN",
            "OUT",
            "SALDO AKHIR",
            "SO FISIK",
            "SELISIH",
            "HARGA BELI",
            "JML SO FISIK",
            "JUMLAH SALDO",
            "JUMLAH SELISIH",
        ]
        last_col = len(headers) - 1

        company_name = self.env.user.company_id.name or ""
        sheet.merge_range(0, 0, 0, last_col, "LAPORAN HASIL STOCK OPNAME", title_format)
        sheet.merge_range(1, 0, 1, last_col, company_name, subtitle_format)
        periode_text = "Periode: %s s.d. %s" % (start_date, end_date)
        sheet.merge_range(2, 0, 2, last_col, periode_text, subtitle_format)

        header_row = 4
        for col, header in enumerate(headers):
            sheet.write(header_row, col, header, header_format)
            sheet.set_column(col, col, 15)

        sheet.set_column(1, 1, 40)

        row = header_row + 1
        grand_total_saldo = 0
        grand_total_selisih = 0
        grand_total_fisik = 0

        index = 1
        for product in products:
            pid = product.id
            so_awal = so_awal_products.get(pid, 0.0)
            in_qty = move_data[pid]["in_qty"]
            out_qty = move_data[pid]["out_qty"]
            saldo_akhir = so_awal + in_qty - out_qty
            so_fisik = so_fisik_products.get(pid, 0.0)
            selisih = so_fisik - saldo_akhir
            cost_price = product.standard_price

            jumlah_saldo = saldo_akhir * cost_price
            jumlah_selisih = selisih * cost_price
            jumlah_fisik = so_fisik * cost_price

            grand_total_saldo += jumlah_saldo
            grand_total_selisih += jumlah_selisih
            grand_total_fisik += jumlah_fisik

            sheet.write(row, 0, index, text_format)
            sheet.write(row, 1, product.display_name, text_format)
            sheet.write(row, 2, product.uom_id.name, text_format)
            sheet.write(row, 3, so_awal, num_format)
            sheet.write(row, 4, in_qty, num_format)
            sheet.write(row, 5, out_qty, num_format)
            sheet.write(row, 6, saldo_akhir, num_format)
            sheet.write(row, 7, so_fisik, num_format)
            sheet.write(row, 8, selisih, num_format)
            sheet.write(row, 9, cost_price, currency_format)
            sheet.write(row, 10, jumlah_fisik, currency_format)
            sheet.write(row, 11, jumlah_saldo, currency_format)

            if jumlah_selisih < 0:
                sheet.write(row, 12, jumlah_selisih, red_currency_format)
            else:
                sheet.write(row, 12, jumlah_selisih, currency_format)

            row += 1
            index += 1

        sheet.write(row, 0, "GRAND TOTAL", header_format)
        sheet.write(row, 10, grand_total_fisik, bold_currency_format)
        sheet.write(row, 11, grand_total_saldo, bold_currency_format)
        sheet.write(row, 12, grand_total_selisih, bold_currency_format)

        workbook.close()
        output.seek(0)

        # Simpan file ke field binary dan return action download
        filename = f"Laporan Stock Opname {start_date} - {end_date}.xlsx"
        self.write(
            {"excel_file": base64.b64encode(output.read()), "excel_filename": filename}
        )
        output.close()

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=stock.report.wizard&id={self.id}&field=excel_file&download=true&filename={filename}",
            "target": "self",
        }
