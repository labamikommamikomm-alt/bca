# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging


class ReportStockByPeriod(models.AbstractModel):
    _name = "report.breeze_distribution.report_stock_by_period_template"
    _description = "Stock Report by Period"

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = fields.Date.from_string(data.get("start_date"))
        end_date = fields.Date.from_string(data.get("end_date"))

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

        # --- 4. Compile Data & Totals ---
        report_lines = []
        grand_total_saldo = 0.0
        grand_total_selisih = 0.0
        grand_total_fisik = 0.0

        for product in products:
            pid = product.id
            awal = so_awal_products.get(pid, 0.0)
            in_q = move_data[pid]["in_qty"]
            out_q = move_data[pid]["out_qty"]

            saldo_akhir = awal + in_q - out_q
            fisik = so_fisik_products.get(pid, 0.0)

            selisih = fisik - saldo_akhir
            price = product.standard_price

            j_saldo = saldo_akhir * price
            j_selisih = selisih * price
            j_fisik = fisik * price

            grand_total_saldo += j_saldo
            grand_total_selisih += j_selisih
            grand_total_fisik += j_fisik

            report_lines.append(
                {
                    "name": product.display_name,
                    "satuan": product.uom_id.name,
                    "so_awal": awal,
                    "in_qty": in_q,
                    "out_qty": out_q,
                    "saldo_akhir": saldo_akhir,
                    "so_fisik": fisik,
                    "selisih": selisih,
                    "harga_beli": price,
                    "jumlah_saldo": j_saldo,
                    "jumlah_selisih": j_selisih,
                    "jumlah_so_fisik": j_fisik,
                }
            )

        return {
            "doc_ids": docids,
            "report_lines": report_lines,
            "start_date": start_date,
            "end_date": end_date,
            "company_name": self.env.user.company_id.name,
            "grand_total_saldo": grand_total_saldo,
            "grand_total_selisih": grand_total_selisih,
            "grand_total_fisik": grand_total_fisik,
        }
