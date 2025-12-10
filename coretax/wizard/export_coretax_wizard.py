# l10n_id_coretax/wizard/export_coretax_wizard.py
import base64
import io
from odoo import models, fields, _
from odoo.exceptions import UserError
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

class ExportCoretaxWizard(models.TransientModel):
    _name = 'export.coretax.wizard'
    _description = 'Wizard to Export Invoice to Coretax XLSX'

    def action_export_xlsx(self):
        invoice_ids = self.env['account.move'].browse(self._context.get('active_ids', []))
        if not invoice_ids:
            raise UserError(_("Tidak ada invoice yang dipilih untuk diekspor."))

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Library "xlsxwriter" tidak terinstall. Silakan install dengan perintah: pip3 install xlsxwriter'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        # === Sheet 1: Faktur ===
        ws_faktur = workbook.add_worksheet('Faktur')
        company = self.env.user.company_id
        ws_faktur.write('A1', 'NPWP Penjual'); ws_faktur.write('C1', company.vat or '')
        faktur_headers = [
            'Baris', 'Tanggal Faktur', 'Jenis Faktur', 'Kode Transaksi', 'Keterangan Tambahan', 'Dokumen Pendukung', 'Referensi', 'Cap Fasilitas', 'ID TKU Penjual', 'NPWP/NIK Pembeli', 'Jenis ID Pembeli', 'Negara Pembeli', 'Nomor Dokumen Pembeli', 'Nama Pembeli', 'Alamat Pembeli', 'Email Pembeli', 'ID TKU Pembeli'
        ]
        for i, header in enumerate(faktur_headers): ws_faktur.write(2, i, header, header_format)
        
        row_faktur = 3
        for i, inv in enumerate(invoice_ids, start=1):
            partner = inv.partner_id
            ws_faktur.write(row_faktur, 0, i)
            ws_faktur.write(row_faktur, 1, inv.invoice_date.strftime('%d/%m/%Y'))
            ws_faktur.write(row_faktur, 2, inv.jenis_faktur or 'Normal')
            ws_faktur.write(row_faktur, 3, inv.kode_transaksi)
            ws_faktur.write(row_faktur, 4, inv.keterangan_tambahan_faktur or '')
            ws_faktur.write(row_faktur, 5, '')
            ws_faktur.write(row_faktur, 6, inv.name)
            ws_faktur.write(row_faktur, 7, inv.cap_fasilitas or '')
            ws_faktur.write(row_faktur, 8, '')
            ws_faktur.write(row_faktur, 9, partner.vat or partner.nik or '0000000000000000')
            ws_faktur.write(row_faktur, 10, 'TIN' if partner.vat else 'KTP')
            ws_faktur.write(row_faktur, 11, 'IDN')
            ws_faktur.write(row_faktur, 12, '-')
            ws_faktur.write(row_faktur, 13, partner.nama_npwp or partner.name)
            ws_faktur.write(row_faktur, 14, partner.alamat_npwp or partner.contact_address.replace('\n', ' '))
            ws_faktur.write(row_faktur, 15, partner.email or '')
            ws_faktur.write(row_faktur, 16, partner.vat or '000000')
            row_faktur += 1
        ws_faktur.write(row_faktur, 0, 'END')

        # === Sheet 2: DetailFaktur ===
        ws_detail = workbook.add_worksheet('DetailFaktur')
        detail_headers = [
            'Baris', 'Barang/Jasa', 'Kode Barang Jasa', 'Nama Barang/Jasa', 'Nama Satuan Ukur', 'Harga Satuan', 'Jumlah Barang Jasa', 'Total Diskon', 'DPP', 'DPP Nilai Lain', 'Tarif PPN', 'PPN', 'Tarif PPnBM', 'PPnBM'
        ]
        for i, header in enumerate(detail_headers): ws_detail.write(0, i, header, header_format)
        
        row_detail = 1
        for i, inv in enumerate(invoice_ids, start=1):
            for line in inv.invoice_line_ids.filtered(lambda l: not l.display_type):
                ws_detail.write(row_detail, 0, i)
                ws_detail.write(row_detail, 1, line.product_id.barang_jasa if line.product_id else 'A')
                ws_detail.write(row_detail, 2, '300000')
                ws_detail.write(row_detail, 3, line.name)
                ws_detail.write(row_detail, 4, line.product_uom_id.kode_satuan or line.product_uom_id.name)
                ws_detail.write(row_detail, 5, line.price_unit)
                ws_detail.write(row_detail, 6, line.quantity)
                ws_detail.write(row_detail, 7, line.get_total_diskon())
                ws_detail.write(row_detail, 8, line.price_subtotal)
                ws_detail.write(row_detail, 9, line.price_subtotal) # Asumsi DPP Nilai Lain sama dengan DPP
                ws_detail.write(row_detail, 10, (line.tax_ids[0].amount if line.tax_ids else 11))
                ws_detail.write(row_detail, 11, line.price_total - line.price_subtotal)
                ws_detail.write(row_detail, 12, 0); ws_detail.write(row_detail, 13, 0)
                row_detail += 1
        ws_detail.write(row_detail, 0, 'END')

        # === Sheet 3: REF ===
        ws_ref = workbook.add_worksheet('REF')
        ref_headers = ['Baris', 'Jenis Dokumen', 'Nomor Dokumen', 'Tanggal Dokumen']
        for i, header in enumerate(ref_headers): ws_ref.write(0, i, header, header_format)

        row_ref = 1
        for i, inv in enumerate(invoice_ids, start=1):
            for ref in inv.dokumen_referensi_ids:
                ws_ref.write(row_ref, 0, i)
                ws_ref.write(row_ref, 1, ref.jenis_dokumen or '')
                ws_ref.write(row_ref, 2, ref.nomor_dokumen or '')
                ws_ref.write(row_ref, 3, ref.tanggal_dokumen.strftime('%d/%m/%Y') if ref.tanggal_dokumen else '')
                row_ref += 1
        ws_ref.write(row_ref, 0, 'END')

        # === Sheet 4: Keterangan ===
        ws_ket = workbook.add_worksheet('Keterangan')
        ket_headers = ['Baris', 'Keterangan']
        for i, header in enumerate(ket_headers): ws_ket.write(0, i, header, header_format)

        row_ket = 1
        for i, inv in enumerate(invoice_ids, start=1):
            if inv.keterangan_coretax:
                ws_ket.write(row_ket, 0, i)
                ws_ket.write(row_ket, 1, inv.keterangan_coretax)
                row_ket += 1
        ws_ket.write(row_ket, 0, 'END')

        workbook.close()
        output.seek(0)
        
        file_name = f"Coretax_Export_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': file_name, 'datas': base64.b64encode(output.read()), 'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    # def action_export_xml(self):
    #     invoice_ids = self.env['account.move'].browse(self._context.get('active_ids', []))
    #     if not invoice_ids:
    #         raise UserError(_("Tidak ada invoice yang dipilih untuk diekspor."))
            
    #     company = self.env.user.company_id
    #     if not company.vat:
    #         raise UserError(_("NPWP Perusahaan (Penjual) belum diatur di data perusahaan!"))

    #     # Root element
    #     root = Element('TaxInvoiceBulk')
    #     root.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
    #     root.set('xsi:noNamespaceSchemaLocation', "TaxInvoice.xsd")
        
    #     # TIN Penjual
    #     SubElement(root, 'TIN').text = company.vat.translate(str.maketrans('', '', '.-'))

    #     # List Of Tax Invoice
    #     list_of_tax_invoice = SubElement(root, 'ListOfTaxInvoice')

    #     # Fungsi helper untuk menambahkan elemen dengan aman
    #     def _add_sub(parent, tag, value):
    #         sub = SubElement(parent, tag)
    #         # Mengonversi semua nilai ke string dan memastikan tidak ada nilai None
    #         sub.text = str(value) if value is not None else ''
    #         return sub

    #     for inv in invoice_ids:
    #         partner = inv.partner_id
    #         tax_invoice = SubElement(list_of_tax_invoice, 'TaxInvoice')
            
    #         # Data Header Faktur
    #         _add_sub(tax_invoice, 'TaxInvoiceDate', inv.invoice_date.strftime('%Y-%m-%d'))
    #         _add_sub(tax_invoice, 'TaxInvoiceOpt', inv.jenis_faktur or 'Normal')
    #         # DIUBAH: Tambahkan fallback '01' jika kode transaksi kosong
    #         _add_sub(tax_invoice, 'TrxCode', inv.kode_transaksi or '01')
    #         _add_sub(tax_invoice, 'AddInfo', inv.keterangan_tambahan_faktur or '')
    #         _add_sub(tax_invoice, 'CustomDoc', '')
    #         _add_sub(tax_invoice, 'CustomDocMonthYear', inv.invoice_date.strftime('%m%Y'))
    #         _add_sub(tax_invoice, 'RefDesc', inv.name)
    #         _add_sub(tax_invoice, 'FacilityStamp', inv.cap_fasilitas or '')
    #         _add_sub(tax_invoice, 'SellerIDTKU', (company.vat.translate(str.maketrans('', '', '.-')) or '') + '000000')

    #         # Data Pembeli
    #         buyer_tin = (partner.vat or partner.nik or '0000000000000000').translate(str.maketrans('', '', '.-'))
    #         _add_sub(tax_invoice, 'BuyerTin', buyer_tin if partner.vat else '0000000000000000')
    #         _add_sub(tax_invoice, 'BuyerDocument', 'TIN' if partner.vat else 'National ID')
    #         _add_sub(tax_invoice, 'BuyerCountry', 'IDN') 
    #         _add_sub(tax_invoice, 'BuyerDocumentNumber', '-' if partner.vat else partner.nik or '0000000000000000')
    #         _add_sub(tax_invoice, 'BuyerName', partner.nama_npwp or partner.name)
    #         _add_sub(tax_invoice, 'BuyerAdress', (partner.alamat_npwp or partner.contact_address or '').replace('\n', ' '))
    #         _add_sub(tax_invoice, 'BuyerEmail', partner.email or '')
    #         # DIUBAH: Gunakan buyer_tin yang lebih aman dan sudah punya fallback
    #         _add_sub(tax_invoice, 'BuyerIDTKU', buyer_tin + '000000' if partner.vat else '000000')

    #         # Detail Barang/Jasa
    #         list_of_good_service = SubElement(tax_invoice, 'ListOfGoodService')
    #         for line in inv.invoice_line_ids.filtered(lambda l: not l.display_type and l.price_subtotal > 0):
    #             good_service = SubElement(list_of_good_service, 'GoodService')
                
    #             vat_rate = line.tax_ids[0].amount if line.tax_ids else 11.0
                
    #             # DIUBAH: Hitung nilai OtherTaxBase dan bulatkan
    #             other_tax_base_val = line.price_subtotal if str(inv.kode_transaksi) != "04" else round(line.price_subtotal * 11 / 12, 2)
                
    #             total_discount = round(line.discount / 100 * (line.price_unit * line.quantity), 2)
    #             vat_amount = round(line.price_total - line.price_subtotal, 2)
                
    #             _add_sub(good_service, 'Opt', 'A')
    #             _add_sub(good_service, 'Code', '300000')
    #             _add_sub(good_service, 'Name', line.name)
    #             _add_sub(good_service, 'Unit', line.product_uom_id.kode_satuan or line.product_uom_id.name)
    #             _add_sub(good_service, 'Price', round(line.price_unit, 2))
    #             _add_sub(good_service, 'Qty', line.quantity) # Qty biasanya tidak perlu dibulatkan
    #             _add_sub(good_service, 'TotalDiscount', total_discount)
    #             _add_sub(good_service, 'TaxBase', round(line.price_subtotal, 2))
    #             _add_sub(good_service, 'OtherTaxBase', other_tax_base_val)
    #             _add_sub(good_service, 'VATRate', int(vat_rate))
    #             _add_sub(good_service, 'VAT', vat_amount)
    #             _add_sub(good_service, 'STLGRate', 0)
    #             _add_sub(good_service, 'STLG', 0)

    #     # Generate XML string
    #     xml_string = tostring(root, 'utf-8')
    #     pretty_xml_string = minidom.parseString(xml_string).toprettyxml(indent="  ")
        
    #     # Buat file untuk di-download
    #     file_name = f"Coretax_Export_{fields.Date.today()}.xml"
    #     file_data = base64.b64encode(pretty_xml_string.encode('utf-8'))
        
    #     attachment = self.env['ir.attachment'].create({
    #         'name': file_name,
    #         'datas': file_data,
    #         'type': 'binary',
    #         'mimetype': 'application/xml'
    #     })

    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/web/content/{attachment.id}?download=true',
    #         'target': 'self',
    #     }
    def action_export_xml(self):
        invoice_ids = self.env['account.move'].browse(self._context.get('active_ids', []))
        if not invoice_ids:
            raise UserError(_("Tidak ada invoice yang dipilih untuk diekspor."))
            
        company = self.env.user.company_id
        if not company.vat:
            raise UserError(_("NPWP Perusahaan (Penjual) belum diatur di data perusahaan!"))

        # Root element
        root = Element('TaxInvoiceBulk')
        root.set('xmlns:xsi', "http://www.w3.org/2001/XMLSchema-instance")
        root.set('xsi:noNamespaceSchemaLocation', "TaxInvoice.xsd")
        
        # TIN Penjual
        SubElement(root, 'TIN').text = company.vat.translate(str.maketrans('', '', '.-'))

        # List Of Tax Invoice
        list_of_tax_invoice = SubElement(root, 'ListOfTaxInvoice')

        # Fungsi helper untuk menambahkan elemen dengan aman
        def _add_sub(parent, tag, value):
            sub = SubElement(parent, tag)
            # Mengonversi semua nilai ke string dan memastikan tidak ada nilai None
            sub.text = str(value) if value is not None else ''
            return sub

        for inv in invoice_ids:
            partner = inv.partner_id
            tax_invoice = SubElement(list_of_tax_invoice, 'TaxInvoice')
            
            # Data Header Faktur
            _add_sub(tax_invoice, 'TaxInvoiceDate', inv.invoice_date.strftime('%Y-%m-%d'))
            _add_sub(tax_invoice, 'TaxInvoiceOpt', inv.jenis_faktur or 'Normal')
            # DIUBAH: Tambahkan fallback '01' jika kode transaksi kosong
            _add_sub(tax_invoice, 'TrxCode', inv.kode_transaksi or '01')
            _add_sub(tax_invoice, 'AddInfo', inv.keterangan_tambahan_faktur or '')
            _add_sub(tax_invoice, 'CustomDoc', '')
            _add_sub(tax_invoice, 'CustomDocMonthYear', inv.invoice_date.strftime('%m%Y'))
            _add_sub(tax_invoice, 'RefDesc', inv.name)
            _add_sub(tax_invoice, 'FacilityStamp', inv.cap_fasilitas or '')
            _add_sub(tax_invoice, 'SellerIDTKU', (company.vat.translate(str.maketrans('', '', '.-')) or '') + '000000')

            # Data Pembeli
            buyer_tin = (partner.vat or partner.nik or '0000000000000000').translate(str.maketrans('', '', '.-'))
            _add_sub(tax_invoice, 'BuyerTin', buyer_tin)
            _add_sub(tax_invoice, 'BuyerDocument', 'TIN')
            _add_sub(tax_invoice, 'BuyerCountry', 'IDN') 
            _add_sub(tax_invoice, 'BuyerDocumentNumber', '-')
            _add_sub(tax_invoice, 'BuyerName', partner.nama_npwp or partner.name)
            _add_sub(tax_invoice, 'BuyerAdress', (partner.alamat_npwp or partner.contact_address or '').replace('\n', ' '))
            _add_sub(tax_invoice, 'BuyerEmail', partner.email or '')
            # DIUBAH: Gunakan buyer_tin yang lebih aman dan sudah punya fallback
            _add_sub(tax_invoice, 'BuyerIDTKU', buyer_tin + '000000')

            # Detail Barang/Jasa
            list_of_good_service = SubElement(tax_invoice, 'ListOfGoodService')
            for line in inv.invoice_line_ids.filtered(lambda l: not l.display_type and l.price_subtotal > 0):
                good_service = SubElement(list_of_good_service, 'GoodService')
                
                vat_rate = line.tax_ids[0].amount if line.tax_ids else 11.0
                
                # DIUBAH: Hitung nilai OtherTaxBase dan bulatkan
                other_tax_base_val =  round(line.price_subtotal * 11 / 12, 2)
                
                total_discount = round(line.discount / 100 * (line.price_unit * line.quantity), 2)
                vat_amount = round(line.price_total - line.price_subtotal, 2)
                
                _add_sub(good_service, 'Opt', 'A')
                _add_sub(good_service, 'Code', '300000')
                _add_sub(good_service, 'Name', line.name)
                _add_sub(good_service, 'Unit', line.product_uom_id.kode_satuan or line.product_uom_id.name)
                _add_sub(good_service, 'Price', round(line.price_unit, 2))
                _add_sub(good_service, 'Qty', line.quantity) # Qty biasanya tidak perlu dibulatkan
                _add_sub(good_service, 'TotalDiscount', total_discount)
                _add_sub(good_service, 'TaxBase', round(line.price_subtotal, 2))
                _add_sub(good_service, 'OtherTaxBase', other_tax_base_val)
                _add_sub(good_service, 'VATRate', int(vat_rate))
                _add_sub(good_service, 'VAT', vat_amount)
                _add_sub(good_service, 'STLGRate', 0)
                _add_sub(good_service, 'STLG', 0)

        # Generate XML string
        xml_string = tostring(root, 'utf-8')
        pretty_xml_string = minidom.parseString(xml_string).toprettyxml(indent="  ")
        
        # Buat file untuk di-download
        file_name = f"Coretax_Export_{fields.Date.today()}.xml"
        file_data = base64.b64encode(pretty_xml_string.encode('utf-8'))
        
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/xml'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }