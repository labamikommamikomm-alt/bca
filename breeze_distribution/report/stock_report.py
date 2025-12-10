# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ReportStockByPeriod(models.AbstractModel):
    _name = 'report.breeze_distribution.report_stock_by_period_template'
    _description = 'Stock Report by Period'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("Starting stock report generation with new logic per product.")
        
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')


        start_date = fields.Date.from_string(start_date_str)
        end_date = fields.Date.from_string(end_date_str)
        
        # Ambil semua produk yang aktif
        products = self.env['product.product'].search([('active', '=', True)])

        # --- 1. Hitung Saldo Awal (SO AWAL) per produk ---
        # Ambil semua stock opname yang sudah valid sebelum tanggal mulai
        opnames_before_start = self.env['stock.inventory'].search([
            ('state', '=', 'done'),
            ('date', '<', start_date),
        ], order='date asc') # Urutkan dari yang terlama ke terbaru

        so_awal_products = {}
        # Ulangi setiap opname, nilai yang lebih baru akan menimpa yang lama
        for opname in opnames_before_start:
            for line in opname.line_ids:
                so_awal_products[line.product_id.id] = line.product_qty

        # --- 2. Hitung Stok Masuk & Keluar (IN/OUT) dalam periode ---
        moves = self.env['stock.move'].search([
            ('product_id', 'in', products.ids),
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ])

        move_data = {prod.id: {'in_qty': 0, 'out_qty': 0} for prod in products}
        for move in moves:
            product_id = move.product_id.id
            if product_id not in move_data:
                continue

            if move.location_dest_id.usage == 'internal' and move.location_id.usage != 'internal':
                move_data[product_id]['in_qty'] += move.product_uom_qty
            elif move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                move_data[product_id]['out_qty'] += move.product_uom_qty

        # --- 3. Ambil data Stock Opname Fisik (SO FISIK) dalam periode ---
        opnames_in_period = self.env['stock.inventory'].search([
            ('state', '=', 'done'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ], order='date asc') # Urutkan dari yang terlama ke terbaru

        so_fisik_products = {}
        # Ulangi setiap opname, nilai yang lebih baru akan menimpa yang lama
        for opname in opnames_in_period:
            for line in opname.line_ids:
                so_fisik_products[line.product_id.id] = line.product_qty

        # --- 4. Gabungkan semua data untuk membuat baris laporan ---
        report_lines = []
        for product in products:
            product_id = product.id
            
            # Ambil data dari kamus yang sudah kita siapkan
            so_awal = so_awal_products.get(product_id, 0) # Default 0 jika belum pernah di-opname
            in_qty = move_data[product_id]['in_qty']
            out_qty = move_data[product_id]['out_qty']
            so_fisik = so_fisik_products.get(product_id, 0) # Default 0 jika tidak di-opname dalam periode
            
            # Lakukan perhitungan
            saldo_akhir = so_awal + in_qty - out_qty
            selisih = so_fisik - saldo_akhir if so_fisik > 0 else 0 # Hitung selisih hanya jika ada SO Fisik
            harga_beli = product.standard_price

            jumlah_saldo = saldo_akhir * harga_beli
            jumlah_selisih = selisih * harga_beli

            report_lines.append({
                'name': product.display_name,
                'satuan': product.uom_id.name,
                'so_awal': so_awal,
                'in_qty': in_qty,
                'out_qty': out_qty,
                'saldo_akhir': saldo_akhir,
                'so_fisik': so_fisik,
                'selisih': selisih,
                'harga_beli': harga_beli,
                'jumlah_saldo': jumlah_saldo,
                'jumlah_selisih': jumlah_selisih,
            })
        
        _logger.info("Generated %s report lines. Finalizing report...", len(report_lines))
        company = self.env.user.company_id
        company_name = company.name
        _logger.info(f"lalala {company}")

        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': products,
            'report_lines': report_lines,
            'start_date': start_date,
            'end_date': end_date,
            'company_name': company_name
        }
