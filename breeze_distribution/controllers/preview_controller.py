import datetime
from odoo import http, exceptions, fields, _
from odoo.http import request
from collections import defaultdict # Untuk membantu mengelompokkan data

class RekapPenjualanController(http.Controller):
    @http.route('/distribution/rekap_penjualan/preview/<int:id>', auth='user')
    def previewRekapPenjualan(self, id, **kw):
        def context_timestamp(datetime_obj): 
            """
            Helper function to convert datetime to user's timezone.
            """
            return fields.Datetime.context_timestamp(request.env.user, datetime_obj)
        
        # Get customer
        customer = request.env["res.partner"].sudo().search([("id","=", id)], limit=1)
        if not customer:
            raise exceptions.UserError(_("Customer not found."))
        
        customerArray = [customer.id, customer.name]
        
        # Get invoices for the specific customer and journal type 'sale'
        invoices = request.env['account.move'].sudo().search([
            ('journal_id.type', '=', 'sale'), 
            ('partner_id', '=', customer.id),
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'), 
        ])
        
        company = request.env.user.company_id
        company_name = company.name

        rows = {}
        total_nota = 0 
        total_ppn = 0  
        total = 0      
        currency_id = request.env.user.company_id.currency_id

        # Cache sales_discount_account untuk efisiensi
        sales_discount_account = request.env['account.account'].sudo().search([
            ('name', 'ilike', 'Sales Discount'),
            ('company_id', '=', company.id)
        ], limit=1)
        if not sales_discount_account:
            sales_discount_account = request.env['account.account'].sudo().search([
                ('code', '=', '42000070'), 
                ('company_id', '=', company.id)
            ], limit=1)

        for rec in invoices:
            # Gunakan defaultdict untuk mengelompokkan baris produk berdasarkan sale_line_id
            # ini akan membantu kita menggabungkan baris produk dengan baris diskonnya
            grouped_product_details = defaultdict(lambda: {
                'nama_barang': '',
                'qty': 0.0,
                'sat': '',
                'harga_bruto_per_satuan': 0.0,
                'diskon_persen': 0.0,
                'jumlah_bruto': 0.0,
                'jumlah_diskon': 0.0, # Akan diisi dengan total diskon untuk produk ini
                'jumlah_netto': 0.0,  # Akan diisi dengan total netto untuk produk ini
                'product_id': False, # Untuk menyimpan ref produk_id
                'sale_line_id': False, # Untuk menyimpan ref sale_line_id
            })

            # Langkah 1: Proses semua baris invoice untuk mengumpulkan data
            for inv_line in rec.invoice_line_ids:
                is_explicit_discount_line = False
                
                # Cek apakah ini baris diskon eksplisit yang kita tambahkan
                if sales_discount_account and inv_line.account_id.id == sales_discount_account.id and inv_line.price_unit < 0:
                    is_explicit_discount_line = True
                
                if inv_line.product_id and not is_explicit_discount_line: # Ini adalah baris produk biasa
                    sale_line = inv_line.sale_line_ids[:1] # Ambil sale_line_ids pertama jika ada
                    
                    # Kunci unik untuk mengelompokkan (misal: product_id atau sale_line_id jika unik per invoice)
                    # Jika satu SO line bisa split jadi banyak invoice line (misal karena pajak),
                    # maka gunakan product_id + price_unit (bruto) untuk unik
                    group_key = inv_line.product_id.id 
                    if sale_line: # Jika terkait dengan SO line, gunakan ID SO line sebagai kunci yang lebih spesifik
                        group_key = sale_line.id
                    
                    # Inisialisasi atau update detail produk
                    detail = grouped_product_details[group_key]
                    detail['type'] = 'product'
                    detail['nama_barang'] = inv_line.product_id.name
                    detail['qty'] += inv_line.quantity # Akumulasi qty jika ada beberapa baris untuk produk yang sama
                    detail['sat'] = inv_line.product_uom_id.name # Asumsi satuan sama untuk qty terakumulasi
                    detail['harga_bruto_per_satuan'] = inv_line.price_unit # Ini adalah harga bruto
                    detail['diskon_persen'] = sale_line.discount if sale_line else 0.0
                    detail['jumlah_bruto'] += inv_line.price_unit * inv_line.quantity
                    detail['jumlah_netto'] += inv_line.price_subtotal # Ini adalah subtotal netto dari baris produk
                    detail['product_id'] = inv_line.product_id.id
                    detail['sale_line_id'] = sale_line.id if sale_line else False
                    
                elif is_explicit_discount_line: # Ini adalah baris diskon eksplisit
                    # Cari sale_line_id yang terkait dengan nama diskon (misal "Diskon Penjualan untuk PRODUK X")
                    # Ini adalah cara yang sedikit 'hacky' tapi seringkali satu-satunya cara karena tidak ada korelasi langsung
                    # antara baris diskon eksplisit dan sale_line_id yang spesifik, kecuali melalui nama.
                    # Asumsi: Nama diskon mencantumkan nama produk.
                    
                    # Ekstrak nama produk dari nama baris diskon jika mengikuti pola "Diskon Penjualan untuk %s"
                    # Ini mungkin perlu disesuaikan jika nama diskon tidak konsisten
                    product_name_in_discount = inv_line.name.replace(_("Diskon Penjualan untuk "), "").split(' (')[0]
                    
                    # Cari product_id yang cocok dari produk yang sudah diproses di invoice ini
                    # Atau bisa juga dari sale_line_map yang sudah dibuat di awal
                    found_group_key = None
                    for key, val in grouped_product_details.items():
                        # Coba cocokkan berdasarkan nama produk atau product_id
                        if val['product_id']: # Pastikan ada product_id di detail produk
                            if val['product_id'] == inv_line.product_id.id: # Jika baris diskon memiliki product_id
                                found_group_key = key
                                break
                            # Fallback: cocokkan nama produk (kurang disarankan, bisa duplikat nama)
                            # elif product_name_in_discount and product_name_in_discount in val['nama_barang']:
                            #     found_group_key = key
                            #     break
                                
                    if found_group_key:
                        # Tambahkan jumlah diskon ke baris produk terkait
                        grouped_product_details[found_group_key]['jumlah_diskon'] += abs(inv_line.price_subtotal) # Jumlah diskon positif
                        # Sesuaikan jumlah_netto dari produk yang sama
                        grouped_product_details[found_group_key]['jumlah_netto'] += inv_line.price_subtotal # Karena ini nilai negatif
                    else:
                        # Jika tidak dapat menemukan baris produk terkait,
                        # mungkin tampilkan baris diskon ini sebagai baris terpisah
                        # atau log peringatan. Untuk tujuan laporan 1 baris, ini bisa diabaikan
                        # atau ditambahkan ke suatu 'lain-lain' jika diperlukan.
                        # Untuk saat ini, kita akan mengabaikannya jika tidak ada produk terkait yang ditemukan.
                        _logger.warning(f"Could not find matching product line for explicit discount line: {inv_line.name} (Invoice ID: {rec.id})")

            # Ubah defaultdict menjadi list biasa untuk template
            invoice_lines_details = list(grouped_product_details.values())

            # Pastikan perhitungan netto akhir untuk setiap baris produk yang digabungkan
            # Jika ada baris diskon yang tidak terasosiasi, ini bisa jadi masalah
            for index, detail in enumerate(invoice_lines_details):
                if detail['type'] == 'product':
                    # Hitung ulang jumlah_netto berdasarkan jumlah_bruto dan jumlah_diskon yang sudah terakumulasi
                    detail['jumlah_netto'] = detail['jumlah_bruto'] - detail['jumlah_diskon']
                    detail['idx'] = index

            # Accumulate totals for the report summary
            total_nota += rec.amount_untaxed
            total_ppn += rec.amount_tax
            total += rec.amount_total
            
            # Store invoice details and its product lines
            rows[rec.id] = {
              'faktur': rec.name,
              'customer': rec.partner_id.name,
              'sub_total': rec.amount_untaxed,
              'ppn': rec.amount_tax,
              'total': rec.amount_total,
              'currency_id': currency_id,
              'tgl_faktur': rec.invoice_date or rec.date, 
              'invoice_lines_details': invoice_lines_details, # List of ALL combined invoice line details
            }
        
        lines = []
        for i in rows:
            lines.append(rows[i])
            
        # Setup data for the report template
        data = {
            "company_name": company_name,
            "data":{
                "customer_id" : customerArray,
            },
            "context_timestamp": context_timestamp,
            "lines": lines, 
            'tn': total_nota, 
            'tp': total_ppn,  
            'total': total,   
            'currency_id': currency_id,
        }
        
        return request.render('breeze_distribution.report_rekap_penjualan', data)