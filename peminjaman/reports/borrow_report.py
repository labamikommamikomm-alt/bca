from odoo import api, models, fields, _
from odoo.tools import format_date
from odoo.exceptions import UserError
import datetime

class ReportBorrowReturn(models.AbstractModel):
    _name = 'report.peminjaman.borrow_report_template'
    _description = 'Peminjaman/Pengembalian Report (Grouped)'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        start_date = fields.Date.from_string(data['form']['start_date'])
        end_date = fields.Date.from_string(data['form']['end_date'])
        
        partner_id_tuple = data['form']['partner_id']
        partner_filter_obj = self.env['res.partner']
        if partner_id_tuple:
            partner_filter_obj = self.env['res.partner'].browse(partner_id_tuple[0])

        report_type = data['form']['report_type']
        show_returned_items = data['form']['show_returned_items']

        domain = [
            ('state', 'in', ['posted']),
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            '|', ('is_peminjaman', '=', True), ('is_pengembalian', '=', True)
        ]

        if partner_filter_obj:
            domain.append(('partner_id', '=', partner_filter_obj.id))

        # IMPORTANT: If report_type is 'borrowed' and show_returned_items is True,
        # we need to search for ALL borrow AND return documents to correctly calculate returns.
        # If report_type is just 'borrowed' (no returns shown), then only 'is_peminjaman'
        # If report_type is just 'returned', then only 'is_pengembalian'

        # Refined domain based on report_type and show_returned_items
        if report_type == 'borrowed' and not show_returned_items:
            # Only show borrowed items, no need to consider returns
            domain = [d for d in domain if d != ('is_pengembalian', '=', True)]
            domain.append(('is_peminjaman', '=', True))
        elif report_type == 'returned':
            # Only show returned items, no need to consider borrows
            domain = [d for d in domain if d != ('is_peminjaman', '=', True)]
            domain.append(('is_pengembalian', '=', True))
        # Else (report_type == 'borrowed' AND show_returned_items OR 'all'),
        # the original '|', ('is_peminjaman', '=', True), ('is_pengembalian', '=', True) is good.
        
        moves = self.env['account.move'].search(domain, order="invoice_date asc, name asc")

        # --- Aggregation Logic ---
        # Structure: { partner_id: { product_id: { borrowed_qty: X, returned_qty: Y, product_name: '', uom_name: '' } } }
        grouped_data = {}

        for move in moves:
            partner_id = move.partner_id.id
            partner_name = move.partner_id.name

            if partner_id not in grouped_data:
                grouped_data[partner_id] = {
                    'partner_name': partner_name,
                    'products': {}
                }

            for line in move.invoice_line_ids.filtered(lambda l: l.product_id):
                product_id = line.product_id.id
                product_name = line.product_id.display_name
                uom_name = line.product_uom_id.name

                if product_id not in grouped_data[partner_id]['products']:
                    grouped_data[partner_id]['products'][product_id] = {
                        'product_name': product_name,
                        'uom_name': uom_name,
                        'total_borrowed_qty': 0.0,
                        'total_returned_qty': 0.0,
                    }

                if move.is_peminjaman:
                    grouped_data[partner_id]['products'][product_id]['total_borrowed_qty'] += line.quantity
                elif move.is_pengembalian:
                    # For a return, we add to returned_qty.
                    # This implies 'Pengembalian' invoices are created for actual returns of borrowed items.
                    grouped_data[partner_id]['products'][product_id]['total_returned_qty'] += line.quantity

        # --- Prepare data for QWeb ---
        # Convert grouped_data into a list of dictionaries for easier iteration in QWeb
        report_output = []
        for partner_id, partner_data in grouped_data.items():
            partner_products = []
            for product_id, product_data in partner_data['products'].items():
                partner_products.append(product_data)
            
            # Sort products by name for consistent report output
            partner_products.sort(key=lambda x: x['product_name'])

            report_output.append({
                'partner_name': partner_data['partner_name'],
                'products': partner_products
            })
        
        # Sort partners by name for consistent report output
        report_output.sort(key=lambda x: x['partner_name'])


        company = self.env.company
        current_datetime_formatted = fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'data': data['form'],
            'docs': moves, # Still pass the moves if needed for debugging or other info, but main data is report_output
            'report_output': report_output, # This is the main aggregated data
            'start_date': format_date(self.env, start_date, date_format='dd/MM/yyyy'),
            'end_date': format_date(self.env, end_date, date_format='dd/MM/yyyy'),
            'partner_name_filter': partner_filter_obj.name if partner_filter_obj else 'Semua Partner', # Name for filter display
            'company': company,
            'current_datetime': current_datetime_formatted,
            'report_type': report_type, # Pass this to QWeb if needed for conditional display
            'show_returned_items': show_returned_items, # Pass this to QWeb if needed for conditional display
        }