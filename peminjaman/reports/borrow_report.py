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

        grouped_data = {}

        # 1. Fetch Borrowed Items (Purchase Orders)
        if report_type == 'borrowed' or (report_type == 'all' or show_returned_items):
            po_domain = [
                ('state', 'in', ['purchase', 'done']),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('is_peminjaman', '=', True)
            ]
            if partner_filter_obj:
                po_domain.append(('partner_id', '=', partner_filter_obj.id))
            
            purchases = self.env['purchase.order'].search(po_domain)
            for po in purchases:
                partner_id = po.partner_id.id
                if partner_id not in grouped_data:
                    grouped_data[partner_id] = {'partner_name': po.partner_id.name, 'products': {}}
                
                for line in po.order_line.filtered(lambda l: l.product_id):
                    pid = line.product_id.id
                    if pid not in grouped_data[partner_id]['products']:
                        grouped_data[partner_id]['products'][pid] = {
                            'product_name': line.product_id.display_name,
                            'uom_name': line.product_uom.name,
                            'total_borrowed_qty': 0.0,
                            'total_returned_qty': 0.0,
                        }
                    grouped_data[partner_id]['products'][pid]['total_borrowed_qty'] += line.product_qty

        # 2. Fetch Returned Items (Sale Orders)
        if report_type == 'returned' or (report_type == 'borrowed' and show_returned_items) or report_type == 'all':
            so_domain = [
                ('state', 'in', ['sale', 'done']),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('is_pengembalian', '=', True)
            ]
            if partner_filter_obj:
                so_domain.append(('partner_id', '=', partner_filter_obj.id))
                
            sales = self.env['sale.order'].search(so_domain)
            for so in sales:
                partner_id = so.partner_id.id
                if partner_id not in grouped_data:
                    grouped_data[partner_id] = {'partner_name': so.partner_id.name, 'products': {}}
                
                for line in so.order_line.filtered(lambda l: l.product_id):
                    pid = line.product_id.id
                    if pid not in grouped_data[partner_id]['products']:
                        grouped_data[partner_id]['products'][pid] = {
                            'product_name': line.product_id.display_name,
                            'uom_name': line.product_uom.name,
                            'total_borrowed_qty': 0.0,
                            'total_returned_qty': 0.0,
                        }
                    grouped_data[partner_id]['products'][pid]['total_returned_qty'] += line.product_uom_qty

        # --- Prepare data for QWeb ---
        report_output = []
        for partner_id, partner_data in grouped_data.items():
            partner_products = []
            for product_id, product_data in partner_data['products'].items():
                partner_products.append(product_data)
            
            partner_products.sort(key=lambda x: x['product_name'])
            report_output.append({
                'partner_name': partner_data['partner_name'],
                'products': partner_products
            })
        
        report_output.sort(key=lambda x: x['partner_name'])


        company = self.env.company
        current_datetime_formatted = fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order', # Updated doc_model from 'account.move' as we decouple
            'data': data['form'],
            'docs': self.env['purchase.order'].browse(), # Returning an empty recordset just to fulfill 'docs' if it's strictly expected.
            'report_output': report_output, # This is the main aggregated data
            'start_date': format_date(self.env, start_date, date_format='dd/MM/yyyy'),
            'end_date': format_date(self.env, end_date, date_format='dd/MM/yyyy'),
            'partner_name_filter': partner_filter_obj.name if partner_filter_obj else 'Semua Partner', # Name for filter display
            'company': company,
            'current_datetime': current_datetime_formatted,
            'report_type': report_type, # Pass this to QWeb if needed for conditional display
            'show_returned_items': show_returned_items, # Pass this to QWeb if needed for conditional display
        }