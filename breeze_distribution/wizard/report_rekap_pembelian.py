from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import base64
import io
import logging 
_logger = logging.getLogger(__name__)
class RekapPembelian(models.TransientModel):
    _name = 'report.rekap_pembelian'
    _description = 'Rekapitulasi Pembelian Report Wizard'


    start_date = fields.Date(string="Tanggal Mulai", required=True, default=fields.Date.today())
    end_date = fields.Date(string="Tanggal Akhir", required=True, default=fields.Date.today())
    supplier = fields.Many2one("res.partner", string="Supplier", help="Kosongkan untuk menyertakan semua supplier.")
    
    # 1. Tambahkan field boolean baru di sini
    show_invoice_total = fields.Boolean(string="Tampilkan Total per Faktur", default=True, help="Jika dicentang, laporan akan menampilkan subtotal untuk setiap faktur.")
    show_product_info = fields.Boolean(string="Tampilkan Informasi Barang", default=True, help="Jika tidak dicentang, laporan tidak menyertakan informasi Produk (hanya total).")

    def _build_comparison_context(self, data):
        result = {}
        result['start_date'] = data['form']['start_date']
        result['end_date'] = data['form']['end_date']
        result['supplier'] = data['form']['supplier'] if data['form']['supplier'] else False
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['start_date', 'end_date', 'supplier', 'show_invoice_total', 'show_product_info'])[0]
        
        if not data['form']['start_date'] or not data['form']['end_date']:
            raise ValidationError("Tanggal Mulai dan Tanggal Akhir harus diisi untuk menghasilkan laporan.")
        if data['form']['start_date'] and data['form']['end_date'] and data['form']['start_date'] > data['form']['end_date']:
            raise ValidationError("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")


        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        
        # This calls the standard PDF report action which automatically handles active_model context.
        return self.env.ref('breeze_distribution.report_rekap_pembelian_action').with_context(landscape=True).report_action(self, data=data)


    def export_excel(self):
        # Check for xlsxwriter dependency
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Library "xlsxwriter" is not installed. Please install it using: pip3 install xlsxwriter'))

        # 1. Get the report object and inject the necessary context
        report_obj = self.env['report.breeze_distribution.report_rekap_pembelian'].with_context(
            active_model=self._name,
            active_ids=self.ids
        )
        
        data = {
            'model': 'report.rekap_pembelian',
            'form': self.read(['start_date', 'end_date', 'supplier', 'show_invoice_total', 'show_product_info'])[0]
        }
        
        # Check date validation again for safety
        if not data['form']['start_date'] or not data['form']['end_date']:
            raise ValidationError("Tanggal Mulai dan Tanggal Akhir harus diisi untuk menghasilkan laporan.")
        if data['form']['start_date'] > data['form']['end_date']:
            raise ValidationError("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")

        # Fetch report data
        report_data = report_obj._get_report_values(self.ids, data=data)
        lines = report_data['lines']
        extra_headers = report_data.get('extra_price_headers', [])
        
        # 2. Create the Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Laporan Pembelian')

        # Setup formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        text_center = workbook.add_format({'align': 'center', 'border': 1})
        text_right = workbook.add_format({'align': 'right', 'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right', 'border': 1})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#BFBFBF', 'border': 1, 'align': 'right'})
        total_currency_format = workbook.add_format({'bold': True, 'bg_color': '#BFBFBF', 'num_format': '#,##0.00', 'align': 'right', 'border': 1})

        # 3. Write Report Header
        total_cols = 13 + len(extra_headers)
        last_col = total_cols - 1
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        subtitle_format = workbook.add_format({'align': 'center', 'italic': True})
        sheet.merge_range(0, 0, 0, last_col, f"LAPORAN DATA PEMBELIAN {report_data['company_name']}", title_format)
        sheet.merge_range(1, 0, 1, last_col, f"Periode: {report_data['start_date_formatted']} - {report_data['end_date_formatted']}", subtitle_format)
        
        # 4. Write Column Headers
        show_prod = data['form']['show_product_info']
        if show_prod:
            headers = ['No', 'No Dok', 'Tgl Faktur', 'Supplier', 'Faktur', 'Nama Barang', 'Qty', 'Satuan', 'Harga', 'Jumlah'] + [h.upper() for h in extra_headers] + ['PPN', 'Sub Total', 'Total']
            col_widths = [5, 10, 15, 30, 20, 40, 10, 8, 15, 15] + [15] * len(extra_headers) + [15, 15, 15]
        else:
            headers = ['No', 'No Dok', 'Tgl Faktur', 'Supplier', 'Faktur', 'Sub Total', 'PPN'] + [h.upper() for h in extra_headers] + ['Total']
            col_widths = [5, 10, 15, 30, 20, 15, 15] + [15] * len(extra_headers) + [15]

        row_num = 4

        for col_num, header in enumerate(headers):
            sheet.write(row_num, col_num, header, header_format)
            sheet.set_column(col_num, col_num, col_widths[col_num])
            
        row_num += 1

        # 5. Write Data Rows
        index = 1
        for line in lines:
            line_products = line['product']
            num_products = len(line_products)

            if not show_prod:
                # Opsi: ringkasan per faktur (tanpa produk)
                sheet.write(row_num, 0, index, text_center)
                sheet.write(row_num, 1, f"{line['no_dok']}", text_center)
                sheet.write(row_num, 2, line['tgl_faktur'].strftime('%d/%m/%Y'), text_center)
                sheet.write(row_num, 3, line['supplier'], text_center)
                sheet.write(row_num, 4, line['faktur'] or '', text_center)
                
                sheet.write_number(row_num, 5, line['sub_total'], currency_format)
                sheet.write_number(row_num, 6, line['ppn'], currency_format)
                
                for idx_h, h in enumerate(extra_headers):
                    col = 7 + idx_h
                    sheet.write_number(row_num, col, line['extra_costs'].get(h, 0.0), currency_format)

                col_total = 7 + len(extra_headers)
                sheet.write_number(row_num, col_total, line['total'], currency_format)

                row_num += 1
                index += 1
            else:
                for i, product in enumerate(line_products):
                    if i == 0:
                        if num_products > 1:
                            sheet.merge_range(row_num, 0, row_num + num_products - 1, 0, index, text_center)
                            sheet.merge_range(row_num, 1, row_num + num_products - 1, 1, f"{line['no_dok']}", text_center)
                            sheet.merge_range(row_num, 2, row_num + num_products - 1, 2, line['tgl_faktur'].strftime('%d/%m/%Y'), text_center)
                            sheet.merge_range(row_num, 3, row_num + num_products - 1, 3, line['supplier'], text_center)
                            sheet.merge_range(row_num, 4, row_num + num_products - 1, 4, line['faktur'] or '', text_center)
                        else:
                            sheet.write(row_num, 0, index, text_center)
                            sheet.write(row_num, 1, f"{line['no_dok']}", text_center)
                            sheet.write(row_num, 2, line['tgl_faktur'].strftime('%d/%m/%Y'), text_center)
                            sheet.write(row_num, 3, line['supplier'], text_center)
                            sheet.write(row_num, 4, line['faktur'] or '', text_center)

                    sheet.write(row_num + i, 5, product['nama_barang'], text_center)
                    sheet.write_number(row_num + i, 6, product['qty'], text_right)
                    sheet.write(row_num + i, 7, product['sat'], text_center)
                    sheet.write_number(row_num + i, 8, product['harga'], currency_format)
                    sheet.write_number(row_num + i, 9, product['jumlah'], currency_format)

                    if i == 0:
                        if num_products > 1:
                            for idx_h, h in enumerate(extra_headers):
                                col = 10 + idx_h
                                val = line['extra_costs'].get(h, 0.0)
                                sheet.merge_range(row_num, col, row_num + num_products - 1, col, val, currency_format)
                            
                            col_ppn = 10 + len(extra_headers)
                            sheet.merge_range(row_num, col_ppn, row_num + num_products - 1, col_ppn, line['ppn'], currency_format)
                            sheet.merge_range(row_num, col_ppn + 1, row_num + num_products - 1, col_ppn + 1, line['sub_total'], currency_format)
                            sheet.merge_range(row_num, col_ppn + 2, row_num + num_products - 1, col_ppn + 2, line['total'], currency_format)
                            
                        else:
                            for idx_h, h in enumerate(extra_headers):
                                col = 10 + idx_h
                                sheet.write_number(row_num + i, col, line['extra_costs'].get(h, 0.0), currency_format)
                            
                            col_ppn = 10 + len(extra_headers)
                            sheet.write_number(row_num + i, col_ppn, line['ppn'], currency_format)
                            sheet.write_number(row_num + i, col_ppn + 1, line['sub_total'], currency_format)
                            sheet.write_number(row_num + i, col_ppn + 2, line['total'], currency_format)
                
                row_num += num_products
                index += 1
            
        # 6. Write Grand Total
        if show_prod:
            sheet.merge_range(row_num, 0, row_num, 9, 'TOTAL:', total_format)
            col_offset = 10
            
            grand_extra_totals = report_data.get('grand_extra_totals', {})
            for idx_h, h in enumerate(extra_headers):
                col = col_offset + idx_h
                sheet.write_number(row_num, col, grand_extra_totals.get(h, 0.0), total_currency_format)
                
            col_ppn = col_offset + len(extra_headers)
            sheet.write_number(row_num, col_ppn, report_data['grand_ppn'], total_currency_format)
            sheet.write_number(row_num, col_ppn + 1, report_data['grand_sub_total'], total_currency_format)
            sheet.write_number(row_num, col_ppn + 2, report_data['grand_total_amount'], total_currency_format)
        else:
            sheet.merge_range(row_num, 0, row_num, 4, 'TOTAL:', total_format)
            col_offset = 5
            
            sheet.write_number(row_num, col_offset, report_data['grand_sub_total'], total_currency_format)
            sheet.write_number(row_num, col_offset + 1, report_data['grand_ppn'], total_currency_format)
            
            grand_extra_totals = report_data.get('grand_extra_totals', {})
            for idx_h, h in enumerate(extra_headers):
                col = col_offset + 2 + idx_h
                sheet.write_number(row_num, col, grand_extra_totals.get(h, 0.0), total_currency_format)
            
            col_total = col_offset + 2 + len(extra_headers)
            sheet.write_number(row_num, col_total, report_data['grand_total_amount'], total_currency_format)

        # Finalize
        workbook.close()
        output.seek(0)
        
        file_name = f"Laporan_Rekap_Pembelian_{fields.Date.today()}.xlsx"
        file_data = base64.b64encode(output.read())
        
        # 7. FIX: Menggunakan ir.actions.act_url untuk memastikan download berhasil
        attachment = self.env['ir.attachment'].create({
            'name': file_name,
            'datas': file_data,
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
