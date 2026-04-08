# peminjaman/reports/borrow_report_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class BorrowReportWizard(models.TransientModel):
    _name = 'report.borrow.report.wizard'
    _description = 'Wizard for Peminjaman/Pengembalian Report'

    start_date = fields.Date(string="Tanggal Mulai", required=True, default=fields.Date.today())
    end_date = fields.Date(string="Tanggal Akhir", required=True, default=fields.Date.today())
    partner_id = fields.Many2one('res.partner', string="Partner", help="Kosongkan untuk semua partner.")
    report_type = fields.Selection([
        ('borrowed', 'Peminjaman'),
        ('returned', 'Pengembalian'),
        ('all', 'Semua')
    ], string="Tipe Laporan", default='all', required=True)
    show_returned_items = fields.Boolean(string="Tampilkan Barang Dikembalikan", default=True,
        help="Jika Peminjaman, centang untuk menampilkan barang yang sudah dikembalikan.")

    def check_report(self):
        data = {
            'model': self._name,
            'form': self.read(['start_date', 'end_date', 'partner_id', 'report_type', 'show_returned_items'])[0]
        }
        # Correctly pass partner_id as a tuple if it exists
        if data['form']['partner_id']:
            data['form']['partner_id'] = data['form']['partner_id']
        else:
            data['form']['partner_id'] = False # Ensure it's False if empty

        return self.env.ref('peminjaman.action_report_borrow_return').report_action(self, data=data)

    def export_excel(self):
        # 1. Reuse identical fetching & grouping logic from the PDF report to ensure exact match
        start_date = self.start_date
        end_date = self.end_date
        partner_id = self.partner_id
        report_type = self.report_type
        show_returned_items = self.show_returned_items

        grouped_data = {}

        if report_type == 'borrowed' or (report_type == 'all' or show_returned_items):
            po_domain = [
                ('state', 'in', ['purchase', 'done']),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('is_peminjaman', '=', True)
            ]
            if partner_id:
                po_domain.append(('partner_id', '=', partner_id.id))
            
            purchases = self.env['purchase.order'].search(po_domain)
            for po in purchases:
                pid = po.partner_id.id
                if pid not in grouped_data:
                    grouped_data[pid] = {'partner_name': po.partner_id.name, 'products': {}}
                
                for line in po.order_line.filtered(lambda l: l.product_id):
                    prod_id = line.product_id.id
                    if prod_id not in grouped_data[pid]['products']:
                        grouped_data[pid]['products'][prod_id] = {
                            'product_name': line.product_id.display_name,
                            'uom_name': line.product_uom.name,
                            'total_borrowed_qty': 0.0,
                            'total_returned_qty': 0.0,
                        }
                    grouped_data[pid]['products'][prod_id]['total_borrowed_qty'] += line.product_qty

        if report_type == 'returned' or (report_type == 'borrowed' and show_returned_items) or report_type == 'all':
            so_domain = [
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('is_pengembalian', '=', True)
            ]
            if partner_id:
                so_domain.append(('partner_id', '=', partner_id.id))
                
            sales = self.env['sale.order'].search(so_domain)
            for so in sales:
                pid = so.partner_id.id
                if pid not in grouped_data:
                    grouped_data[pid] = {'partner_name': so.partner_id.name, 'products': {}}
                
                for line in so.order_line.filtered(lambda l: l.product_id):
                    prod_id = line.product_id.id
                    if prod_id not in grouped_data[pid]['products']:
                        grouped_data[pid]['products'][prod_id] = {
                            'product_name': line.product_id.display_name,
                            'uom_name': line.product_uom.name,
                            'total_borrowed_qty': 0.0,
                            'total_returned_qty': 0.0,
                        }
                    grouped_data[pid]['products'][prod_id]['total_returned_qty'] += line.product_uom_qty

        report_output = []
        for pid, pdata in grouped_data.items():
            partner_products = list(pdata['products'].values())
            partner_products.sort(key=lambda x: x['product_name'])
            report_output.append({
                'partner_name': pdata['partner_name'],
                'products': partner_products
            })
        report_output.sort(key=lambda x: x['partner_name'])

        # 2. XlsxWriter Engine
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Borrow Report')

        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        meta_label_format = workbook.add_format({'bold': True})
        meta_val_format = workbook.add_format({'align': 'left'})
        subheader_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'left'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})

        # Write Header Metadata
        sheet.merge_range('A1:F1', 'LAPORAN REKAP PEMINJAMAN DAN PENGEMBALIAN BARANG', title_format)

        sheet.write('A3', 'Dari Tanggal:', meta_label_format)
        sheet.write('B3', str(start_date.strftime('%d/%m/%Y')), meta_val_format)
        sheet.write('E3', 'Hingga Tanggal:', meta_label_format)
        sheet.write('F3', str(end_date.strftime('%d/%m/%Y')), meta_val_format)

        partner_name_str = partner_id.name if partner_id else 'Semua Partner'
        sheet.write('A4', 'Partner Filter:', meta_label_format)
        sheet.write('B4', partner_name_str, meta_val_format)
        sheet.write('E4', 'Dicetak Pada:', meta_label_format)
        sheet.write('F4', str(fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')), meta_val_format)

        sheet.set_column(0, 0, 5)   # No.
        sheet.set_column(1, 1, 40)  # Nama Barang
        sheet.set_column(2, 3, 18)  # Qty Pinjam/Kembali
        sheet.set_column(4, 4, 10)  # Satuan
        sheet.set_column(5, 5, 15)  # Sisa Pinjam

        row = 6
        if not report_output:
            sheet.merge_range(row, 0, row, 5, 'Tidak ada data transaksi ditemukan dalam periode ini dengan filter yang dipilih.', text_center)
        else:
            for group in report_output:
                sheet.merge_range(row, 0, row, 5, f"Partner: {group['partner_name']}", subheader_format)
                row += 1

                headers = ['No.', 'Nama Barang', 'Total Qty Pinjam', 'Total Qty Kembali', 'Satuan', 'Sisa Pinjam']
                for col_num, h in enumerate(headers):
                    sheet.write(row, col_num, h, header_format)
                row += 1

                product_num = 1
                for product in group['products']:
                    sheet.write(row, 0, product_num, text_center)
                    sheet.write(row, 1, product['product_name'] or '', text_left)
                    sheet.write_number(row, 2, product['total_borrowed_qty'], num_format)
                    sheet.write_number(row, 3, product['total_returned_qty'], num_format)
                    sheet.write(row, 4, product['uom_name'] or '', text_center)
                    
                    sisa = product['total_borrowed_qty'] - product['total_returned_qty']
                    sheet.write_number(row, 5, sisa, num_format)
                    
                    product_num += 1
                    row += 1
                row += 1 # extra spacing between tables

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Laporan_Peminjaman_Pengembalian.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'report.borrow.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }