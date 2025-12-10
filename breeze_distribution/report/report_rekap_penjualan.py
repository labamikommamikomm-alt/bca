from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import json


class ReportPenjualan(models.AbstractModel):
    _name = 'report.breeze_distribution.report_rekap_penjualan'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        # form_data = data['form']
        # raise ValidationError(data['form']['from_date'])


        invoice = self.env['account.move'].sudo().search([('journal_id.type', '=', 'sale'), 
            ('partner_id', '=', data['form']['customer_id'][0])])
        
        company = self.env.user.company_id

        company_name = company.name

        rows = {}
        total_nota = 0
        total_ppn = 0
        total = 0
        currency_id = company.currency_id
        for rec in invoice:
            barang = {}
            barangs = []
            for product in rec.invoice_line_ids:
                if product.move_id.id == rec.id:
                    barang[product.id] = {
                      'nama_barang': product.product_id.name,
                      'qty': product.quantity,
                      'sat': product.product_uom_id.name,
                      'harga': product.price_unit,
                      'jumlah': product.price_subtotal
                    }
            for i in barang:
                barangs.append(barang[i])
            total_nota += rec.amount_untaxed
            total_ppn += rec.amount_tax
            total += rec.amount_total
            currency_id = rec.currency_id
            rows[rec.id] = {
              'no_dok': rec.sequence_char_doc,
              'faktur': rec.name,
              'customer': rec.partner_id.name,
              'sales': rec.team_id.name,
              'sub_total': rec.amount_untaxed,
              'ppn': rec.amount_tax,
              'product': barangs,
              'total': rec.amount_total,
              'kota': rec.partner_id.city,
              'currency_id': rec.currency_id,
              'tgl_cetak': rec.invoice_date,
              'tgl_faktur': rec.date,
            }
        
      

        lines = []
        for i in rows:
            lines.append(rows[i])

        # raise ValidationError(lines['no_nota'])
        return {
          'lines': lines,
          'doc_ids': docids,
          'company_name': company_name,
          'docs': docs,
          'data': data['form'],
          'tn': total_nota,
          'tp': total_ppn,
          'total': total,
          'currency_id': currency_id
        }