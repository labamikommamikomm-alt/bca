from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class ExportVendorBillWizard(models.TransientModel):
    _name = "wizard.export.vendor.bill"
    _description = "Export Vendor Bill to PDF"

    show_nomor = fields.Boolean("Nomor", default=True)
    show_partner = fields.Boolean("Invoice Partner Display Name", default=True)
    show_date = fields.Boolean("Invoice/Bill Date", default=True)
    show_due_date = fields.Boolean("Batas Waktu", default=True)
    show_ref = fields.Boolean("Referensi", default=True)
    show_tax_number = fields.Boolean("Tax Number", default=True)
    show_untaxed_amount = fields.Boolean("Untaxed Amount Signed", default=True)
    show_total = fields.Boolean("Total Signed", default=True)
    show_grand_total = fields.Boolean("Grand Total", default=True)
    show_last_payment_date = fields.Boolean("Tanggal Pembayaran", default=True)
    show_last_payment_method = fields.Boolean("Metode Pembayaran", default=True)
    show_status = fields.Boolean("Status Pembayaran", default=True)

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            raise UserError(_("No records selected."))

        # Compile data to pass to the report
        data = {
            'form': self.read(['show_nomor', 'show_partner', 'show_date', 'show_due_date', 
                               'show_ref', 'show_tax_number', 'show_untaxed_amount', 
                               'show_total', 'show_grand_total', 'show_last_payment_date', 
                               'show_last_payment_method', 'show_status'])[0],
            'active_ids': active_ids
        }
        
        return self.env.ref('breeze_distribution.action_report_export_vendor_bill').report_action(self, data=data)

    def export_excel(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return

        docs = self.env['account.move'].browse(active_ids)
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Vendor Bills')

        # Formats
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1, 'align': 'center'})
        text_center = workbook.add_format({'border': 1, 'align': 'center'})
        text_left = workbook.add_format({'border': 1, 'align': 'left'})
        text_right = workbook.add_format({'border': 1, 'align': 'right'})
        currency_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0'})
        date_format = workbook.add_format({'border': 1, 'align': 'center', 'num_format': 'dd/mm/yyyy'})
        grand_total_label = workbook.add_format({'bold': True, 'bg_color': '#f9f9f9', 'border': 1, 'align': 'right'})
        grand_total_val = workbook.add_format({'bold': True, 'bg_color': '#f9f9f9', 'border': 1, 'align': 'right', 'num_format': '#,##0'})

        sheet.merge_range('A1:L1', 'Rekap Pembayaran Hutang', title_format)

        headers = []
        if self.show_nomor:
            headers.extend(['No.', 'Nomor'])
        if self.show_partner:
            headers.append('Invoice Partner')
        if self.show_date:
            headers.append('Tanggal Faktur')
        if self.show_due_date:
            headers.append('Batas Waktu')
        if self.show_ref:
            headers.append('Referensi')
        if self.show_tax_number:
            headers.append('Tax Number')
        if self.show_untaxed_amount:
            headers.append('Untaxed Amount')
        if self.show_total:
            headers.append('Total')
        if self.show_last_payment_date:
            headers.append('Tanggal Pembayaran')
        if self.show_last_payment_method:
            headers.append('Metode Pembayaran')
        if self.show_status:
            headers.append('Status Pembayaran')

        row = 2
        for col_num, header in enumerate(headers):
            sheet.write(row, col_num, header, header_format)
            sheet.set_column(col_num, col_num, 15) # Default width

        row += 1
        num = 1
        cumulative_grand_total = 0.0

        for o in docs:
            col = 0
            if self.show_nomor:
                sheet.write(row, col, num, text_center)
                col += 1
                sheet.write(row, col, o.name or '', text_center)
                col += 1
            if self.show_partner:
                sheet.write(row, col, o.partner_id.display_name or '', text_left)
                col += 1
            if self.show_date:
                if o.invoice_date:
                    sheet.write_datetime(row, col, o.invoice_date, date_format)
                else:
                    sheet.write(row, col, '', text_center)
                col += 1
            if self.show_due_date:
                if o.invoice_date_due:
                    sheet.write_datetime(row, col, o.invoice_date_due, date_format)
                else:
                    sheet.write(row, col, '', text_center)
                col += 1
            if self.show_ref:
                sheet.write(row, col, o.ref or '', text_center)
                col += 1
            if self.show_tax_number:
                sheet.write(row, col, o.l10n_id_tax_number or '', text_center)
                col += 1
            if self.show_untaxed_amount:
                sheet.write_number(row, col, o.amount_untaxed_signed or 0.0, currency_format)
                col += 1
            if self.show_total:
                sheet.write_number(row, col, o.amount_total_signed or 0.0, currency_format)
                col += 1
            if self.show_last_payment_date:
                if o.last_payment_date:
                    sheet.write_datetime(row, col, o.last_payment_date, date_format)
                else:
                    sheet.write(row, col, '', text_center)
                col += 1
            if self.show_last_payment_method:
                sheet.write(row, col, o.last_payment_method_name or '', text_center)
                col += 1
            if self.show_status:
                state_map = {
                    'not_paid': 'Not Paid',
                    'in_payment': 'In Payment',
                    'paid': 'Paid',
                    'partial': 'Partially Paid',
                    'reversed': 'Reversed',
                    'invoicing_legacy': 'Invoicing App Legacy'
                }
                status_text = state_map.get(o.payment_state, '')
                sheet.write(row, col, status_text, text_center)
                col += 1
            
            num += 1
            if self.show_grand_total:
                cumulative_grand_total += o.amount_total
            
            row += 1

        if self.show_grand_total:
            # Determine colspan based on the exact same logic
            colspan_count = 0
            if self.show_nomor: colspan_count += 2
            if self.show_partner: colspan_count += 1
            if self.show_date: colspan_count += 1
            if self.show_due_date: colspan_count += 1
            if self.show_ref: colspan_count += 1
            if self.show_tax_number: colspan_count += 1
            if self.show_untaxed_amount: colspan_count += 1

            sheet.merge_range(row, 0, row, colspan_count - 1, 'Total Keseluruhan', grand_total_label)
            sheet.write_number(row, colspan_count, cumulative_grand_total, grand_total_val)
            
            # Pad the rest
            pad_col = colspan_count + 1
            if self.show_last_payment_date:
                sheet.write(row, pad_col, '', grand_total_label)
                pad_col += 1
            if self.show_last_payment_method:
                sheet.write(row, pad_col, '', grand_total_label)
                pad_col += 1
            if self.show_status:
                sheet.write(row, pad_col, '', grand_total_label)
                pad_col += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Rekap_Pembayaran_Hutang.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': 'wizard.export.vendor.bill',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
