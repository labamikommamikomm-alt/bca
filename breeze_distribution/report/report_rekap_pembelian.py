from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json
from odoo.tools import format_date
import datetime

class ReportPembelian(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_pembelian'
    _description = 'Rekapitulasi Pembelian Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # FIX: We now allow it to proceed if 'data' is provided, 
        # and only strictly check context if 'data' is missing (standard report check).
        # We will ensure the Transient Model (Wizard) provides active_model for the direct call.
        if not data.get('form'):
             # If data['form'] is missing, we check standard report context
             if not self.env.context.get('active_model'):
                 raise UserError("Form content is missing, this report cannot be printed.")

        # The active_model is needed here to instantiate the self.env[model]
        model = self.env.context.get('active_model') or 'report.rekap_pembelian' # Use wizard model as fallback
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        
        # Data preparation logic remains the same
        supplier_id = data['form']['supplier'][0] if data['form']['supplier'] else False
        start_date = fields.Date.from_string(data['form']['start_date'])
        end_date = fields.Date.from_string(data['form']['end_date'])

        domain = [
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('tanggal_faktur', '>=', start_date),
            ('tanggal_faktur', '<=', end_date),
        ]
        if 'is_peminjaman' in self.env['account.move']._fields:
            domain.append(('is_peminjaman', '=', False))

        if supplier_id:
            domain.append(('partner_id', '=', supplier_id))
        
        invoices = self.env['account.move'].sudo().search(domain, order="tanggal_faktur asc, name asc")
        
        company = self.env.user.company_id
        company_name = company.name

        rows = {}
        currency_id = self.env.user.company_id.currency_id

        grand_sub_total = 0.0
        grand_ppn = 0.0
        grand_total_amount = 0.0

        for rec in invoices:
            barangs = []
            currency_id = rec.currency_id
            
            for product in rec.invoice_line_ids.filtered(lambda l: not l.display_type):
                barangs.append({
                  'nama_barang': product.product_id.name,
                  'qty': product.quantity,
                  'sat': product.product_uom_id.name,
                  'harga': product.price_unit,
                  'jumlah': product.price_subtotal
                })
            
            total_extra_cost = 0.0
            if hasattr(rec, 'extra_cost_journal_id') and rec.extra_cost_journal_id:
                cost_lines = rec.extra_cost_journal_id.line_ids.filtered(lambda l: l.debit > 0)
                for cost_line in cost_lines:
                    barangs.append({
                        'nama_barang': f"(Biaya) {cost_line.name}",
                        'qty': 0.0,
                        'sat': '',
                        'harga': 0.0,
                        'jumlah': cost_line.debit,
                    })
                    total_extra_cost += cost_line.debit

            sub_total_with_costs = rec.amount_untaxed + total_extra_cost
            total_with_costs = rec.amount_total + total_extra_cost
            
            no_dok_val = rec.name

            rows[rec.id] = {
                'no_dok': no_dok_val,
                'tgl_cetak': rec.tanggal_faktur,
                'tgl_faktur': rec.tanggal_faktur,
                'supplier': rec.partner_id.name,
                'faktur': rec.ref,
                'product': barangs,
                'total': total_with_costs,
                'ppn': rec.amount_tax,
                'sub_total': sub_total_with_costs
            }
            
            grand_sub_total += sub_total_with_costs
            grand_ppn += rec.amount_tax
            grand_total_amount += total_with_costs
            
        lines = list(rows.values())

        current_datetime_formatted = fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        return {
            'lines': lines,
            'doc_ids': docids,
            'company_name': company_name,
            'docs': docs,
            'data': data['form'],
            'currency_id': currency_id,
            'start_date_formatted': format_date(self.env, start_date, date_format='dd/MM/yyyy'),
            'end_date_formatted': format_date(self.env, end_date, date_format='dd/MM/yyyy'),
            'current_datetime': current_datetime_formatted,
            'grand_sub_total': grand_sub_total,
            'grand_ppn': grand_ppn,
            'grand_total_amount': grand_total_amount,
        }
    
