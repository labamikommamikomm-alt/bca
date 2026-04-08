from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class ExportInvoiceRecapWizard(models.TransientModel):
    _name = 'export.invoice.recap.wizard'
    _description = 'Export Invoice Recap Wizard'

    judul = fields.Char(string="Judul Laporan", required=True, default="Rekap Invoice")

    def _get_selected_invoices(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError(_("Tidak ada invoice yang dipilih."))
        
        invoices = self.env['account.move'].browse(active_ids)
        if any(inv.move_type not in ('out_invoice', 'out_refund') for inv in invoices):
            raise UserError(_("Harap pilih Customer Invoice (Faktur Penjualan) atau Credit Note saja."))
        return invoices

    def action_print_pdf(self):
        invoices = self._get_selected_invoices()
        data = {
            'form': {
                'judul': self.judul,
                'invoice_ids': invoices.ids,
            }
        }
        return self.env.ref('breeze_distribution.report_invoice_recap_action').report_action(self, data=data)

    def action_export_excel(self):
        if not xlsxwriter:
            raise UserError(_("Module xlsxwriter belum terinstall di Python Anda."))

        invoices = self._get_selected_invoices()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Rekap Invoice')

        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#b3cefc', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        num_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})

        # Write Title
        sheet.merge_range('A1:K1', self.judul.upper(), title_format)

        headers = ['No', 'Tanggal Faktur', 'No Faktur', 'Customer', 'Wilayah/Kota', 'Sales', 'Total Tagihan', 'Sisa Tagihan', 'Status Pembayaran', 'Status']
        for col, h in enumerate(headers):
            sheet.write(3, col, h, header_format)
            
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:F', 20)
        sheet.set_column('G:H', 15)
        sheet.set_column('I:J', 15)

        row = 4
        idx = 1
        
        # Sort invoices by date or string
        sorted_invoices = invoices.sorted(key=lambda x: (x.invoice_date or fields.Date.today(), x.name or ''))

        for inv in sorted_invoices:
            payment_state_dict = dict(inv._fields['payment_state'].selection)
            state_dict = dict(inv._fields['state'].selection)
            
            p_state = payment_state_dict.get(inv.payment_state, inv.payment_state) if inv.payment_state else ''
            i_state = state_dict.get(inv.state, inv.state) if inv.state else ''
            
            sales_name = inv.invoice_user_id.name if inv.invoice_user_id else (inv.team_id.name if inv.team_id else '')

            sheet.write(row, 0, idx, text_center)
            sheet.write(row, 1, inv.invoice_date.strftime('%d/%m/%Y') if inv.invoice_date else '', text_center)
            sheet.write(row, 2, inv.name or '', text_left)
            sheet.write(row, 3, inv.partner_id.name or '', text_left)
            sheet.write(row, 4, inv.partner_id.city or '', text_left)
            sheet.write(row, 5, sales_name, text_left)
            sheet.write_number(row, 6, inv.amount_total, num_format)
            sheet.write_number(row, 7, inv.amount_residual, num_format)
            sheet.write(row, 8, p_state, text_center)
            sheet.write(row, 9, i_state, text_center)
            
            idx += 1
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'{self.judul.replace(" ", "_")}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'export.invoice.recap.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
