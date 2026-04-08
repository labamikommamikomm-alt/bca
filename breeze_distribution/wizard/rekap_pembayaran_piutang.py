from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class RekapPembayaranPiutang(models.TransientModel):
    _name = 'report.rekap_pembayaran_piutang'

    date_from = fields.Date(string="Invoice Starting Date")
    date_to = fields.Date(string="Invoice Ending Date")
    user_id = fields.Many2one('res.users', string="Kolektor / Sales")
    journal_id = fields.Many2one('account.journal', string="Bank / Kas", domain=[('type', 'in', ['bank', 'cash'])])
    payment_date_from = fields.Date(string="Payment Starting Date")
    payment_date_to = fields.Date(string="Payment Ending Date")

    def _build_comparison_context(self, data):
        result = {}
        result['date_from'] = data['form']['date_from']
        result['date_to'] = data['form']['date_to']
        return result

    def _get_report_data(self):
        # We need to construct the logic to fetch account.payment or account.move based on the filters.
        # However, the existing PDF report gets data directly from the wizard context. 
        # We'll rely on the report model report.breeze_distribution.report_rekap_pembayaran_piutang to process this.
        data = {}
        data['form'] = self.read(['date_from', 'date_to', 'user_id', 'journal_id', 'payment_date_from', 'payment_date_to'])[0]
        
        # fix tuple serialization for many2one
        if data['form']['user_id']:
            data['form']['user_id'] = data['form']['user_id'][0]
        if data['form']['journal_id']:
            data['form']['journal_id'] = data['form']['journal_id'][0]
            
        return data

    def check_report(self):
        data = self._get_report_data()
        comparison_context = self._build_comparison_context(data)
        data['form']['comparison_context'] = comparison_context
        return self.env.ref('breeze_distribution.report_rekap_pembayaran_piutang_action').with_context(landscape=True).report_action(self, data=data)

    def export_excel(self):
        data = self._get_report_data()
        report_model = self.env['report.breeze_distribution.report_rekap_pembayaran_piutang']
        report_values = report_model._get_report_values(self.ids, data=data)
        lines = report_values.get('lines', [])
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Pembayaran Piutang')

        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#b3cefc', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        subtotal_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'right', 'num_format': '#,##0'})

        sheet.merge_range('A1:J1', 'LAPORAN PEMBAYARAN PIUTANG', title_format)

        sheet.write('A3', 'Tipe Filter', workbook.add_format({'bold': True}))
        # Add basic filter strings
        sheet.write('A4', f"Invoice Date: {data['form']['date_from'] or '-'} to {data['form']['date_to'] or '-'}")
        sheet.write('A5', f"Payment Date: {data['form']['payment_date_from'] or '-'} to {data['form']['payment_date_to'] or '-'}")

        headers = ['No', 'Faktur', 'Tanggal', 'Customer', 'Tgl lunas', 'Keterangan', 'Admin', 'Saldo', 'PPN', 'PPh', 'Bayar']
        for col, h in enumerate(headers):
            sheet.write(6, col, h, header_format)
            
        sheet.set_column('B:B', 20)
        sheet.set_column('C:E', 15)
        sheet.set_column('D:D', 30)

        row = 7
        for line in lines:
            sheet.merge_range(row, 0, row, 10, f"Penagih : {line['penagih']}", workbook.add_format({'bold': True, 'bg_color': '#f2f2f2'}))
            row += 1
            idx = 1
            for x in line['lines']:
                sheet.write(row, 0, idx, text_center)
                sheet.write(row, 1, x.get('faktur', ''), text_left)
                sheet.write(row, 2, x.get('tanggal', '').strftime('%d/%m/%Y') if hasattr(x.get('tanggal'), 'strftime') else str(x.get('tanggal','')), text_center)
                sheet.write(row, 3, f"{x.get('customer', '')} ({x.get('sales', '')})", text_left)
                
                tgl_lunas_str = ', '.join([t.strftime('%d/%m/%Y') for t in x.get('tgl_lunas', [])])
                sheet.write(row, 4, tgl_lunas_str, text_center)
                
                ket_str = f"{x.get('keterangan', '')} " + ', '.join([f"({j})" for j in x.get('jenis', [])])
                sheet.write(row, 5, ket_str, text_left)
                
                admin_val = 0
                pph_val = 0
                for tax in x.get('taxes', []):
                    if tax.get('nama') == 'admin':
                        admin_val += tax.get('jumlah', 0)
                    else:
                        pph_val += tax.get('jumlah', 0)
                        
                sheet.write_number(row, 6, admin_val, num_format)
                sheet.write_number(row, 7, x.get('saldo', 0), num_format)
                sheet.write_number(row, 8, x.get('ppn', 0), num_format)
                sheet.write_number(row, 9, pph_val, num_format)
                sheet.write_number(row, 10, x.get('bayar', 0), num_format)
                
                idx += 1
                row += 1
                
            sheet.merge_range(row, 0, row, 5, 'Sub Total', subtotal_format)
            sheet.write_number(row, 6, line.get('total_admin', 0), subtotal_format)
            sheet.write_number(row, 7, line.get('total_saldo', 0), subtotal_format)
            sheet.write_number(row, 8, line.get('total_ppn', 0), subtotal_format)
            sheet.write_number(row, 9, line.get('total_pph', 0), subtotal_format)
            sheet.write_number(row, 10, line.get('total_bayar', 0), subtotal_format)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Pembayaran_Piutang.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'report.rekap_pembayaran_piutang',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }