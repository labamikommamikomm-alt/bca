from odoo import models, fields, api
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


    def _build_comparison_context(self, data):
        result = {}
        result['start_date'] = data['form']['start_date']
        result['end_date'] = data['form']['end_date']
        result['supplier'] = data['form']['supplier'] if data['form']['supplier'] else False
        return result

    def check_report(self):
        data = {}
        data['form'] = self.read(['start_date', 'end_date', 'supplier', 'show_invoice_total'])[0]
        
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
            'form': self.read(['start_date', 'end_date', 'supplier', 'show_invoice_total'])[0]
        }
        
        # Check date validation again for safety
        if not data['form']['start_date'] or not data['form']['end_date']:
            raise ValidationError("Tanggal Mulai dan Tanggal Akhir harus diisi untuk menghasilkan laporan.")
        if data['form']['start_date'] > data['form']['end_date']:
            raise ValidationError("Tanggal Mulai tidak boleh lebih besar dari Tanggal Akhir.")

        # Fetch report data
        report_data = report_obj._get_report_values(self.ids, data=data)
        lines = report_data['lines']
        
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
        sheet.merge_range('A1:L1', f"LAPORAN DATA PEMBELIAN {report_data['company_name']}", 
                          workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'}))
        sheet.merge_range('A2:L2', f"Periode: {report_data['start_date_formatted']} - {report_data['end_date_formatted']}",
                          workbook.add_format({'align': 'center', 'italic': True}))
        
        # 4. Write Column Headers
        headers = ['No Dok', 'Tgl Faktur', 'Supplier', 'Faktur', 'Nama Barang', 'Qty', 'Sat', 'Harga', 'Jumlah', 'Sub Total', 'PPN', 'Total']
        col_widths = [10, 15, 30, 20, 40, 10, 8, 15, 15, 15, 15, 15] 
        row_num = 4

        for col_num, header in enumerate(headers):
            sheet.write(row_num, col_num, header, header_format)
            sheet.set_column(col_num, col_num, col_widths[col_num])
            
        row_num += 1

        # 5. Write Data Rows (unchanged logic for merging/data population)
        for line in lines:
            line_products = line['product']
            num_products = len(line_products)

            for i, product in enumerate(line_products):
                if i == 0:
                    if num_products > 1:
                        sheet.merge_range(row_num, 0, row_num + num_products - 1, 0, f"{line['no_dok']}", text_center)
                        sheet.merge_range(row_num, 1, row_num + num_products - 1, 1, line['tgl_faktur'].strftime('%d/%m/%Y'), text_center)
                        sheet.merge_range(row_num, 2, row_num + num_products - 1, 2, line['supplier'], text_center)
                        sheet.merge_range(row_num, 3, row_num + num_products - 1, 3, line['faktur'] or '', text_center)
                    else:
                        sheet.write(row_num, 0, f"{line['no_dok']}", text_center)
                        sheet.write(row_num, 1, line['tgl_faktur'].strftime('%d/%m/%Y'), text_center)
                        sheet.write(row_num, 2, line['supplier'], text_center)
                        sheet.write(row_num, 3, line['faktur'] or '', text_center)

                sheet.write(row_num + i, 4, product['nama_barang'], text_center)
                sheet.write_number(row_num + i, 5, product['qty'], text_right)
                sheet.write(row_num + i, 6, product['sat'], text_center)
                sheet.write_number(row_num + i, 7, product['harga'], currency_format)
                sheet.write_number(row_num + i, 8, product['jumlah'], currency_format)

                if i == 0:
                    if num_products > 1:
                        sheet.merge_range(row_num, 9, row_num + num_products - 1, 9, line['sub_total'], currency_format)
                        sheet.merge_range(row_num, 10, row_num + num_products - 1, 10, line['ppn'], currency_format)
                        sheet.merge_range(row_num, 11, row_num + num_products - 1, 11, line['total'], currency_format)
                    else:
                        sheet.write_number(row_num + i, 9, line['sub_total'], currency_format)
                        sheet.write_number(row_num + i, 10, line['ppn'], currency_format)
                        sheet.write_number(row_num + i, 11, line['total'], currency_format)
            
            row_num += num_products
            
        # 6. Write Grand Total
        sheet.merge_range(row_num, 0, row_num, 8, 'TOTAL:', total_format)
        sheet.write_number(row_num, 9, report_data['grand_sub_total'], total_currency_format)
        sheet.write_number(row_num, 10, report_data['grand_ppn'], total_currency_format)
        sheet.write_number(row_num, 11, report_data['grand_total_amount'], total_currency_format)

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
