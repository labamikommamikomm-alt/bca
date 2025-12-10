from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # is_peminjaman flag will be on PO
    is_pengembalian = fields.Boolean(string="Pengembalian Barang", default=False,
        help="Centang jika transaksi ini adalah pengembalian barang. Harga akan diatur menjadi 0.")

    @api.constrains('is_pengembalian')
    def _check_return_flag(self):
        for order in self:
            if order.is_pengembalian and order.state != 'draft' and any(line.price_unit != 0 for line in order.order_line):
                raise ValidationError(_("Untuk pengembalian, semua harga baris harus 0."))

    @api.onchange('is_pengembalian')
    def _onchange_return_flag(self):
        if self.is_pengembalian:
            for line in self.order_line:
                line.price_unit = 0.0
                line.tax_id = False # Remove taxes
            self._recompute_amounts()
        
    def _recompute_amounts(self):
        # Odoo's default recompute will handle this, but forcing it if needed
        # if self.is_pengembalian:
        #    self.amount_untaxed = 0.0
        #    self.amount_tax = 0.0
        #    self.amount_total = 0.0
        pass # Odoo's base onchange_order_line_ids will update totals

    def write(self, vals):
        res = super().write(vals)
        # Recompute totals if flag is changed, to ensure 0
        if 'is_pengembalian' in vals and vals.get('is_pengembalian'):
            for line in self.order_line:
                line.price_unit = 0.0
                line.tax_id = False
            self.order_line._onchange_product_id() # Recompute line totals
            self._amount_all() # Recompute order totals
        return res

    def _prepare_invoice(self):
        """ Override to pass return flag to invoice. """
        invoice_vals = super()._prepare_invoice()
        invoice_vals['is_pengembalian'] = self.is_pengembalian
        return invoice_vals

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_pengembalian_line = fields.Boolean(related='order_id.is_pengembalian', store=True, readonly=False)

    @api.onchange('product_id', 'product_uom_qty', 'price_unit', 'tax_id')
    def _onchange_price_for_return(self):
        """ Set unit price to 0 if it's a return transaction. """
        if self.is_pengembalian_line:
            self.price_unit = 0.0
            self.tax_id = False # Remove taxes as well for 0 price
            # Force recompute of subtotal and order total
            self._onchange_product_id() # This will re-trigger quantity and unit price changes