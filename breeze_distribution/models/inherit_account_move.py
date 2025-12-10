# -*- coding: utf-8 -*-
import json
import string
import base64
import re
from terbilang import Terbilang
from odoo import models, fields, api, exceptions, _
from odoo.tools.misc import get_lang
from dateutil.relativedelta import relativedelta
import logging
from datetime import date

_logger = logging.getLogger(__name__)

class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    FK_HEAD_LIST1 = ['FK', 'KD_JENIS_TRANSAKSI', 'FG_PENGGANTI', 'NOMOR_FAKTUR', 'MASA_PAJAK', 'TAHUN_PAJAK', 'TANGGAL_FAKTUR', 'NPWP', 'NAMA', 'ALAMAT_LENGKAP', 'JUMLAH_DPP', 'JUMLAH_PPN', 'JUMLAH_PPNBM', 'ID_KETERANGAN_TAMBAHAN', 'FG_UANG_MUKA', 'UANG_MUKA_DPP', 'UANG_MUKA_PPN', 'UANG_MUKA_PPNBM', 'KODE_DOKUMEN_PENDUKUNG']
    FK_HEAD_LIST1NIK = ['FK', 'KD_JENIS_TRANSAKSI', 'FG_PENGGANTI', 'NOMOR_FAKTUR', 'MASA_PAJAK', 'TAHUN_PAJAK', 'TANGGAL_FAKTUR', 'NPWP', 'NIK', 'NAMA', 'ALAMAT_LENGKAP', 'JUMLAH_DPP', 'JUMLAH_PPN', 'JUMLAH_PPNBM', 'ID_KETERANGAN_TAMBAHAN', 'FG_UANG_MUKA', 'UANG_MUKA_DPP', 'UANG_MUKA_PPN', 'UANG_MUKA_PPNBM', 'KODE_DOKUMEN_PENDUKUNG']

    LT_HEAD_LIST1 = ['LT', 'NPWP', 'NAMA', 'JALAN', 'BLOK', 'NOMOR', 'RT', 'RW', 'KECAMATAN', 'KELURAHAN', 'KABUPATEN', 'PROPINSI','KODE_POS', 'NOMOR_TELEPON', '', '', '', '', '', '']

    OF_HEAD_LIST1 = ['OF', 'KODE_OBJEK', 'NAMA', 'HARGA_SATUAN', 'JUMLAH_BARANG', 'HARGA_TOTAL', 'DISKON', 'DPP', 'PPN', 'TARIF_PPNBM', 'PPNBM', '', '', '', '', '', '', '', '', '']

    global_tax_ids = fields.One2many(
        'breeze_distribution.gtax_line', 'account_id', string='Global Taxes', store=True)
    type = fields.Char(string='Type', compute='computeType')
    used_bill = fields.Boolean(string='Used', default=False)
    sequence_number_doc = fields.Integer(
        string='Sequence Number Document', default=False)
    sequence_char_doc = fields.Char(string='Sequence Doc', compute='compute_sequence_char')
    tanggal_faktur = fields.Date(string='Tanggal Faktur')
    show_product = fields.Text(string="Show Product")

    def _csv_row(self, data, delimiter=',', quote='"'):
      stringList = []

      # raise ValueError(type(data))
      for x in data:
        stringList.append(str(x).replace(quote, '\\' + quote))

      return quote + (quote + delimiter + quote).join( stringList ) + quote + '\n'


    def name_get(self):
        # if context is None:
        context = dict(self._context)
        # raise exceptions.UserError(json.dumps(context))
        res = []
        if context.get('special_display_name', False):
            for record in self:
                res.append((record.id, str(record.name) +
                           ' - '+str(record.amount_untaxed)))
        else:
            for record in self:
                res.append((record.id, record.name))
        return res

    def compute_sequence_char(self):
        for record in self:
            default = ""

            if record.sequence_number_doc >= 1000:
                default = str(record.sequence_number_doc)
            elif record.sequence_number_doc >= 100:
                default = "0" + str(record.sequence_number_doc)
            elif record.sequence_number_doc >= 10:
                default = "00" + str(record.sequence_number_doc)
            elif record.sequence_number_doc < 10:
                default = "000" + str(record.sequence_number_doc)

            record.sequence_char_doc = default

    def code_inventory(self):
        """
        This method safely finds all Delivery Orders related to an invoice
        and returns them as a comma-separated string.
        Example: 'WH/OUT/0001, WH/OUT/0002'
        """
        # Ensure this method runs on a single invoice record
        self.ensure_one()

        # Find all Sales Orders related to this invoice
        sale_orders = self.invoice_line_ids.sale_line_ids.order_id
        if not sale_orders:
            return "" # Return an empty string if no SO

        # From all found SOs, find all relevant Delivery Orders (stock.picking)
        # We collect all origin names (SO names) to use in one search
        sale_order_names = sale_orders.mapped('name')

        # Find all pickings whose origin is in our list of SO names
        pickings = self.env['stock.picking'].sudo().search([
            ('state', '=', 'done'),
            ('origin', 'in', sale_order_names)
        ])

        # If no pickings are found, return an empty string
        if not pickings:
            return ""

        # Get all names from the found pickings
        picking_names = pickings.mapped('name')

        # Join all names into a single string, separated by ", "
        return ', '.join(picking_names)

    def no_invoice(self):
        so = self.env['sale.order'].sudo().search(
            [('invoice_ids', '=', self.id)])
        return so.name

    def jenis_pembayaran(self):
        jenis = []
        journal = self.env['account.move'].sudo().search(
            [('ref', '=', self.name), '|', ('journal_id.type', '=', 'cash'), ('journal_id.type', '=', 'bank')])
        for rec in journal:
            jenis.append(rec.journal_id.name)
        return ''.join(jenis)

    def tanggal_bayar(self):
        tanggal = []
        journal = self.env['account.move'].sudo().search(
            [('ref', '=', self.name), '|', ('journal_id.type', '=', 'cash'), ('journal_id.type', '=', 'bank')])

        for rec in journal:
            tanggal.append(rec.date.strftime('%d/%m/%Y'))
        return ''.join(tanggal)

    def total_bayar(self):
        for i in self:
            total = total + int(i.global_tax_ids.amount)
        total_bayar = self.amount_total + total

        return total_bayar
    
    # def gets_product_name(self):
    #     product = []
    #     for record in self.invoice_line_ids:
    #         # product.append(record.product_id.name)
        
    #         record.show_product = record.product_id.name
    #     # return ''.join(product)
    # @api.model
    # def create(self , vals):
    #     res = super(InheritAccountMove, self).create(vals)
    #     product = []
    #     for record in self.invoice_line_ids:
    #         product.append(record.product_id.name)
        
    #     self.show_product = ''.join(product)
        
    #     return res
    

    # @api.model
    def bilangan(self):
        t = Terbilang()

        t.parse(str(int(self.amount_total)))

        return t.getresult()

    # --------------------------------------------------------------------------------
    # (REVISED) _compute_name
    # --------------------------------------------------------------------------------
    def _compute_name(self):
        # 1. Panggil super() SATU KALI untuk SEMUA record di 'self'.
        #    Ini akan memberikan nama default ke SEMUA jurnal,
        #    termasuk 'MISC/2025/0001' untuk Miscellaneous
        #    dan 'INV/2025/0001' untuk Invoices.
        super(InheritAccountMove, self)._compute_name()
        
        # 2. Sekarang, baru kita timpa nama HANYA untuk yang kita mau.
        for move in self:
            
            # Terapkan nama kustom HANYA ke invoice/refund yang punya nomor pajak
            if move.move_type in ('out_invoice', 'out_refund') and move.l10n_id_tax_number:
                try:
                    company = move.company_id
                    
                    # Dynamic Year (YY) from invoice date
                    invoice_year = move.invoice_date.year if move.invoice_date else date.today().year
                    two_digit_year = str(invoice_year)[-2:]
                    
                    # Dynamic Branch Prefix
                    branch_prefix = 'P' # TODO: Make this a setting on res.company
                    
                    # Clean Tax Number and get last 8 digits
                    tax_number_clean = move.l10n_id_tax_number.replace('.', '').replace('-', '')
                    
                    if len(tax_number_clean) >= 8:
                        eight_digits = tax_number_clean[-8:] 
                        
                        # Format Final: YY + Prefix + XXXXXXXX
                        final_invoice_name = two_digit_year + branch_prefix + eight_digits
                        
                        # Terapkan nama baru (ini akan MENIMPA nama default 'INV/2025/0001')
                        if move.name != final_invoice_name:
                            move.name = final_invoice_name
                            _logger.info("Invoice ID %s name overridden to custom format: %s", move.id, final_invoice_name)
                    else:
                        _logger.warning("Invoice ID %s: l10n_id_tax_number (%s) too short. Skipping override.", move.id, move.l10n_id_tax_number)
                
                except Exception as e:
                    _logger.error("Error in custom _compute_name for move ID %s: %s", move.id, e)
            
            # 3. JIKA 'move' adalah Miscellaneous ('entry'),
            #    dia tidak akan masuk ke 'if' di atas.
            #    Sehingga, nama default 'MISC/2025/0001' dari super() akan tetap dipakai.

    # --------------------------------------------------------------------------------
    # (REVISED) action_post
    # --------------------------------------------------------------------------------
    def action_post(self):
        """
        Overridden action_post:
        1. Runs the custom 'sequence_number_doc' logic for specified journal types
           (e.g., purchase, general) before posting.
        2. Preserves the credit limit check.
        3. Calls super() to post the entries.
        """
        
        # Tipe jurnal yang ingin kita berikan sequence_number_doc kustom
        # 'out_invoice' & 'out_refund' dikecualikan krn sudah diurus _compute_name
        journal_types_to_sequence = ['purchase', 'general'] 
        
        for rec in self:
            # 1. Tetapkan sequence_number_doc jika belum ada & tipenya cocok
            if (rec.sequence_number_doc == False or rec.sequence_number_doc == 0) and \
               rec.journal_id.type in journal_types_to_sequence:
                
                # Ambil nomor urut berikutnya *khusus untuk tipe jurnal ini*
                sequence = rec._get_latest_sequence(rec.journal_id.type)
                rec.sequence_number_doc = sequence
            
            # 2. Logika Credit Limit Checking (dari kode asli, dipertahankan)
            pay_type = ['out_invoice', 'out_refund', 'out_receipt']
            if rec.partner_id.active_limit and rec.move_type in pay_type \
                    and rec.partner_id.enable_credit_limit:
                if rec.due_amount >= rec.partner_id.blocking_stage:
                    if rec.partner_id.blocking_stage != 0:
                        raise exceptions.UserError(_(
                            "%s is in  Blocking Stage and "
                            "has a due amount of %s %s to pay") % (
                                            rec.partner_id.name, rec.due_amount,
                                            rec.currency_id.symbol))

        # Lanjutkan ke fungsi action_post() standar Odoo
        res = super(InheritAccountMove, self).action_post()
        return res
    
    # --------------------------------------------------------------------------------
    # (REVISED) _get_latest_sequence
    # --------------------------------------------------------------------------------
    def _get_latest_sequence(self, journal_type):
        """
        Mendapatkan 'sequence_number_doc' terakhir untuk tipe jurnal tertentu
        di dalam tahun fiskal berjalan.
        
        :param journal_type: Tipe jurnal ('purchase', 'general', dll.)
        """
        # Pastikan self adalah single record
        self.ensure_one() 
        
        # Tentukan rentang tanggal untuk tahun ini
        # Gunakan invoice_date (untuk bills) atau date (untuk misc)
        move_date = self.invoice_date or self.date or fields.Date.today()
        startDate = move_date.replace(day=1, month=1)
        endDate = startDate + relativedelta(years=1) - relativedelta(days=1)
        
        # Domain pencarian:
        # - Tipe jurnal harus sama
        # - Dalam rentang tahun berjalan
        # - Status sudah 'posted' (agar nomor urut tidak loncat-loncat)
        # - Bukan 'self' (jurnal ini sendiri)
        domain = [
            ('journal_id.type', '=', journal_type),
            ('date', '>=', startDate),
            ('date', '<=', endDate),
            ('state', '=', 'posted'),
            ('id', '!=', self._origin.id), # Pakai _origin.id untuk handle record baru
        ]

        # Cari jurnal terakhir yang diposting dengan tipe & tahun yang sama
        latest_move = self.env['account.move'].search(
            domain, 
            order='sequence_number_doc desc', 
            limit=1
        )

        sequence = 1
        if latest_move:
            # Jika ada, ambil nomornya + 1
            sequence = latest_move.sequence_number_doc + 1

        return sequence

    def generateGlobalTaxes(self):
        for record in self:
            global_tax_enabled = self.env['ir.config_parameter'].sudo(
            ).get_param('account.global_taxes') or False

            if not global_tax_enabled:
                return

            if not record.payment_state in ['not_paid', 'partial']:
                return

            activeGlobalTaxes = self.env['breeze_distribution.global_tax'].search(
                [('active', '=', True)])

            record.write({
                'global_tax_ids': [(5, 0, 0)]
            })

            for tax in activeGlobalTaxes:
                kondisi_terpenuhi = False
                if tax.berlaku_jika:
                    if tax.kondisi == 'lebih':
                        kondisi_terpenuhi = record.amount_untaxed > tax.nilai
                    elif tax.kondisi == 'lebih_sama':
                        kondisi_terpenuhi = record.amount_untaxed >= tax.nilai
                    elif tax.kondisi == 'kurang':
                        kondisi_terpenuhi = record.amount_untaxed < tax.nilai
                    else:
                        kondisi_terpenuhi = record.amount_untaxed <= tax.nilai
                else:
                    kondisi_terpenuhi = True

                if kondisi_terpenuhi:
                    self.env['breeze_distribution.gtax_line'].create({
                        'account_id': record.id,
                        'global_tax_id': tax.id,
                        'amount': record.amount_untaxed * tax.jumlah / 100
                    })

    def computeType(self):
        for record in self:
            record.type = record.journal_id.type

    # --------------------------------------------------------------------------------
    # (REVISED) _generate_efaktur_invoice
    # --------------------------------------------------------------------------------
    def _generate_efaktur_invoice(self, delimiter):

        # res = 
        """Generate E-Faktur for customer invoice."""
        # Invoice of Customer
        company_id = self.company_id
        dp_product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')

        # raise ValueError(type(self.FK_HEAD_LIST1[0]))
        
        # Variabel output_head perlu diinisialisasi di luar loop
        output_head = ""

        for move in self.filtered(lambda m: m.state == 'posted'):

            nik = str(move.partner_id.l10n_id_nik) if not move.partner_id.vat else ''

            if move.l10n_id_replace_invoice_id:
                number_ref = str(move.l10n_id_replace_invoice_id.name) + " replaced by " + str(move.name) + " " + nik
            else:
                number_ref = str(move.name) + " " + nik
                
            invoice_npwp = '000000000000000'
            
            # Inisialisasi list header CSV
            current_fk_head_list = []
            
            if move.partner_id.vat and len(move.partner_id.vat) >= 12:
                
                # Gunakan header standar
                current_fk_head_list = self.FK_HEAD_LIST1
                output_head = '%s%s%s' % (
                    self._csv_row(self.FK_HEAD_LIST1, delimiter),
                    self._csv_row(self.LT_HEAD_LIST1, delimiter),
                    self._csv_row(self.OF_HEAD_LIST1, delimiter),
                )
                
            
                eTax = move._prepare_etax()
                
                invoice_npwp = move.partner_id.vat
            elif (not move.partner_id.vat or len(move.partner_id.vat) < 12) and move.partner_id.nik:
                
                # Gunakan header NIK
                current_fk_head_list = self.FK_HEAD_LIST1NIK
                output_head = '%s%s%s' % (
                    self._csv_row(self.FK_HEAD_LIST1NIK, delimiter),
                    self._csv_row(self.LT_HEAD_LIST1, delimiter),
                    self._csv_row(self.OF_HEAD_LIST1, delimiter),
                )
                
            
                eTax = move._prepare_etax_nik()
                
                eTax['NIK'] = move.partner_id.nik
            else:
                # Jika tidak ada NPWP atau NIK yang valid, mungkin lewati?
                # Atau gunakan header standar dengan NPWP 000
                current_fk_head_list = self.FK_HEAD_LIST1
                output_head = '%s%s%s' % (
                    self._csv_row(self.FK_HEAD_LIST1, delimiter),
                    self._csv_row(self.LT_HEAD_LIST1, delimiter),
                    self._csv_row(self.OF_HEAD_LIST1, delimiter),
                )
                eTax = move._prepare_etax()
                
                
            invoice_npwp = invoice_npwp.replace('.', '').replace('-', '')

            # Here all fields or columns based on eTax Invoice Third Party
            
            # --- (REVISED) ---
            # Use l10n_id_kode_transaksi field directly, default to '01' if empty
            eTax['KD_JENIS_TRANSAKSI'] = move.l10n_id_kode_transaksi or '01'
            # --- (END REVISED) ---
            
            eTax['FG_PENGGANTI'] = move.l10n_id_tax_number[2:3] if move.l10n_id_tax_number and len(move.l10n_id_tax_number) > 2 else '0'
            eTax['NOMOR_FAKTUR'] = move.l10n_id_tax_number[3:] if move.l10n_id_tax_number and len(move.l10n_id_tax_number) > 3 else '0'
            eTax['MASA_PAJAK'] = move.invoice_date.month if move.invoice_date else fields.Date.today().month
            eTax['TAHUN_PAJAK'] = move.invoice_date.year if move.invoice_date else fields.Date.today().year
            
            faktur_date = move.invoice_date or fields.Date.today()
            eTax['TANGGAL_FAKTUR'] = '{0}/{1}/{2}'.format(faktur_date.day, faktur_date.month, faktur_date.year)
            
            eTax['NPWP'] = invoice_npwp
            eTax['NAMA'] = move.partner_id.nama_ktp if eTax['NPWP'] == '000000000000000' else move.partner_id.nama_npwp
            eTax['NIK'] = move.partner_id.nik if move.partner_id.nik else ''
            eTax['ALAMAT_LENGKAP'] = move.partner_id.alamat_ktp if eTax['NPWP'] == '000000000000000' else move.partner_id.alamat_npwp
            eTax['JUMLAH_DPP'] = int(round(move.amount_untaxed, 0)) # currency rounded to the unit
            eTax['JUMLAH_PPN'] = int(round(move.amount_tax, 0))
            
            # --- (REVISED) ---
            # Handle multiple special codes (04, 07, 08)
            special_codes = ['04', '07', '08'] 
            if move.l10n_id_kode_transaksi in special_codes:
                eTax['ID_KETERANGAN_TAMBAHAN'] = '1'
            else:
                eTax['ID_KETERANGAN_TAMBAHAN'] = ''
            # --- (END REVISED) ---
            
            eTax['REFERENSI'] = number_ref
            eTax['KODE_DOKUMEN_PENDUKUNG'] = '0'
            # eTax['COBA'] = '2'

            lines = move.line_ids.filtered(lambda x: x.product_id.id == int(dp_product_id) and x.price_unit < 0 and not x.display_type) if dp_product_id else []
            eTax['FG_UANG_MUKA'] = 0
            eTax['UANG_MUKA_DPP'] = int(abs(sum(lines.mapped('price_subtotal'))))
            eTax['UANG_MUKA_PPN'] = int(abs(sum(lines.mapped(lambda l: l.price_total - l.price_subtotal))))

            company_npwp = company_id.partner_id.vat or '000000000000000'
            company_npwp = company_npwp.replace('.', '').replace('-', '') # Pastikan NPWP perusahaan juga bersih

            # Sesuaikan list value berdasarkan header yang dipakai (NIK atau standar)
            fk_values_list = ['FK']
            for f in current_fk_head_list[1:]:
                fk_values_list.append(eTax.get(f, '')) # Gunakan .get() untuk keamanan
                
            # eTax['JALAN'] = company_id.partner_id.l10n_id_tax_address or company_id.partner_id.street
            eTax['JALAN'] = ''
            eTax['NOMOR_TELEPON'] = company_id.phone or ''

            lt_values_list = ['FAPR', company_npwp, company_id.name] + [eTax.get(f, '') for f in self.LT_HEAD_LIST1[3:]]

            # HOW TO ADD 2 line to 1 line for free product
            free, sales = [], []

            for line in move.line_ids.filtered(lambda l: not l.exclude_from_invoice_tab and not l.display_type):
                # *invoice_line_unit_price is price unit use for harga_satuan's column
                # *invoice_line_quantity is quantity use for jumlah_barang's column
                # *invoice_line_total_price is bruto price use for harga_total's column
                # *invoice_line_discount_m2m is discount price use for diskon's column
                # *line.price_subtotal is subtotal price use for dpp's column
                # *tax_line or free_tax_line is tax price use for ppn's column
                free_tax_line = tax_line = bruto_total = total_discount = 0.0

                for tax in line.tax_ids:
                    if tax.amount > 0:
                        tax_line += line.price_subtotal * (tax.amount / 100.0)

                invoice_line_unit_price = line.price_unit

                invoice_line_total_price = invoice_line_unit_price * line.quantity

                line_dict = {
                    'KODE_OBJEK': line.product_id.default_code or '',
                    'NAMA': line.product_id.name or '',
                    'HARGA_SATUAN': int(invoice_line_unit_price),
                    'JUMLAH_BARANG': line.quantity,
                    'HARGA_TOTAL': int(invoice_line_total_price),
                    'DPP': int(line.price_subtotal),
                    'product_id': line.product_id.id,
                }

                if line.price_subtotal < 0:
                    for tax in line.tax_ids:
                        free_tax_line += (line.price_subtotal * (tax.amount / 100.0)) * -1.0

                    line_dict.update({
                        'DISKON': int(invoice_line_total_price - line.price_subtotal),
                        'PPN': int(free_tax_line),
                    })
                    free.append(line_dict)
                elif line.price_subtotal != 0.0:
                    invoice_line_discount_m2m = invoice_line_total_price - line.price_subtotal

                    line_dict.update({
                        'DISKON': int(invoice_line_discount_m2m),
                        'PPN': int(tax_line),
                    })
                    sales.append(line_dict)

            sub_total_before_adjustment = sub_total_ppn_before_adjustment = 0.0

            # We are finding the product that has affected
            # by free product to adjustment the calculation
            # of discount and subtotal.
            # - the price total of free product will be
            # included as a discount to related of product.
            for sale in sales:
                for f in free:
                    if f['product_id'] == sale['product_id']:
                        sale['DISKON'] = sale['DISKON'] - f['DISKON'] + f['PPN']
                        sale['DPP'] = sale['DPP'] + f['DPP']

                        tax_line = 0

                        for tax in line.tax_ids:
                            if tax.amount > 0:
                                tax_line += sale['DPP'] * (tax.amount / 100.0)

                        sale['PPN'] = int(tax_line)

                        free.remove(f)

                sub_total_before_adjustment += sale['DPP']
                sub_total_ppn_before_adjustment += sale['PPN']
                bruto_total += sale['DISKON']
                total_discount += round(sale['DISKON'], 2)

            output_head += self._csv_row(fk_values_list, delimiter)
            output_head += self._csv_row(lt_values_list, delimiter)
            for sale in sales:
                of_values_list = ['OF'] + [str(sale.get(f, '')) for f in self.OF_HEAD_LIST1[1:-11]] + ['0', '0', '', '', '', '', '', '', '', '', '']
                output_head += self._csv_row(of_values_list, delimiter)
                
        # Pastikan mengembalikan output_head setelah loop selesai
        # raise ValueError(output_head)
        return output_head
        
    def _prepare_etax(self):

        return {'JUMLAH_PPNBM': 0, 'UANG_MUKA_PPNBM': 0, 'BLOK': '', 'NOMOR': '', 'RT': '', 'RW': '', 'KECAMATAN': '', 'KELURAHAN': '', 'KABUPATEN': '', 'PROPINSI': 'JAWA TENGAH', 'KODE_POS': '', '': '', 'JUMLAH_BARANG': 0, 'TARIF_PPNBM': 0, 'PPNBM': 0}
    
    def _prepare_etax_nik(self):

        return {'NIK': '', 'JUMLAH_PPNBM': 0, 'UANG_MUKA_PPNBM': 0, 'BLOK': '', 'NOMOR': '', 'RT': '', 'RW': '', 'KECAMATAN': '', 'KELURAHAN': '', 'KABUPATEN': '', 'PROPINSI': 'JAWA TENGAH', 'KODE_POS': '', '': '', 'JUMLAH_BARANG': 0, 'TARIF_PPNBM': 0, 'PPNBM': 0}



class GlobalTaxLine(models.Model):
    _name = 'breeze_distribution.gtax_line'

    account_id = fields.Many2one('account.move', string='Account')
    global_tax_id = fields.Many2one(
        'breeze_distribution.global_tax', string='Global Tax')
    amount = fields.Monetary(string="Jumlah")
    currency_id = fields.Many2one(
        'res.currency', related='account_id.currency_id')
