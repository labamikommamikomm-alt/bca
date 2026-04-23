from odoo import api, models, fields
from odoo.exceptions import UserError

class ReportPenjualan(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_penjualan'
    
    HEADER_COLOR = '#790000ff' # Ubah di sini untuk ganti warna header di semua laporan

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}
        if not data.get('form'):
            # If called from list view, data['form'] might be missing
            # We use docids to find the records
            docs = self.env['account.move'].browse(docids)
            data['form'] = {
                'customer_id': False,
                'date_from': min(docs.mapped('invoice_date')) if docs and any(docs.mapped('invoice_date')) else False,
                'date_to': max(docs.mapped('invoice_date')) if docs and any(docs.mapped('invoice_date')) else False,
            }
        else:
            docs = False
            
        form_data = data['form']
        
        # 1. Build Search Domain or use docs
        if docs:
            invoices = docs.sudo().filtered(lambda m: m.journal_id.type == 'sale' and m.state != 'cancel' and m.move_type in ('out_invoice', 'out_refund') and m.invoice_date).sorted(key=lambda m: (m.invoice_date or '', m.name or ''), reverse=True)
        else:
            domain = [
                ('journal_id.type', '=', 'sale'),
                ('state', 'not in', ['draft', 'cancel']),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('invoice_date', '!=', False)
            ]
            
            if form_data.get('customer_id'):
                domain.append(('partner_id', '=', form_data['customer_id'][0] if isinstance(form_data['customer_id'], (list, tuple)) else form_data['customer_id']))
                
            if form_data.get('filter_type') == 'period':
                if form_data.get('date_from'):
                    domain.append(('invoice_date', '>=', form_data['date_from']))
                if form_data.get('date_to'):
                    domain.append(('invoice_date', '<=', form_data['date_to']))

            # 2. Get Invoices
            invoices = self.env['account.move'].sudo().search(domain, order='invoice_date desc, name desc')
        
        company = self.env.company
        rows = []
        total_nota = 0
        total_ppn = 0
        total_all = 0
        currency_id = company.currency_id

        # 3. Process Data
        for index, rec in enumerate(invoices):
            line_details = []
            for idx, product in enumerate(rec.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))):
                price_bruto = product.price_unit
                qty = product.quantity
                jumlah_bruto = price_bruto * qty
                discount_amount = jumlah_bruto * (product.discount / 100.0)
                jumlah_netto = product.price_subtotal

                line_details.append({
                    'idx': idx,
                    'nama_barang': product.product_id.name,
                    'qty': qty,
                    'sat': product.product_uom_id.name,
                    'harga_bruto_per_satuan': price_bruto,
                    'diskon_persen': product.discount,
                    'jumlah_bruto': jumlah_bruto,
                    'jumlah_diskon': discount_amount,
                    'jumlah_netto': jumlah_netto,
                })

            total_nota += rec.amount_untaxed
            total_ppn += rec.amount_tax
            total_all += rec.amount_total
            currency_id = rec.currency_id # Use last currency found or company currency

            rows.append({
                'no': index + 1,
                'faktur': rec.name,
                'customer': rec.partner_id.name,
                'sub_total': rec.amount_untaxed,
                'ppn': rec.amount_tax,
                'total': rec.amount_total,
                'tgl_faktur': rec.invoice_date,
                'currency_id': rec.currency_id,
                'invoice_lines_details': line_details,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'report.rekap_penjualan',
            'company_name': company.name,
            'data': form_data,
            'lines': rows,
            'tn': total_nota,
            'tp': total_ppn,
            'total': total_all,
            'currency_id': currency_id,
            'header_color': self.HEADER_COLOR
        }

    