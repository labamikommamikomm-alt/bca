from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_peminjaman = fields.Boolean(string="Peminjaman Barang", default=False,
        help="Centang jika transaksi ini adalah peminjaman barang. Harga akan diatur menjadi 0.")
    # is_pengembalian flag will be on SO

    @api.constrains('is_peminjaman')
    def _check_borrow_flag(self):
        for order in self:
            if order.is_peminjaman and order.state != 'draft' and any(line.price_unit != 0 for line in order.order_line):
                raise ValidationError(_("Untuk peminjaman, semua harga baris harus 0."))

    @api.onchange('is_peminjaman')
    def _onchange_borrow_flag(self):
        if self.is_peminjaman:
            for line in self.order_line:
                line.price_unit = 0.0
                line.taxes_id = False # Remove taxes
            self._recompute_amounts()
        
    def _recompute_amounts(self):
        # Odoo's default recompute will handle this, but forcing it if needed
        # if self.is_peminjaman:
        #    self.amount_untaxed = 0.0
        #    self.amount_tax = 0.0
        #    self.amount_total = 0.0
        pass # Odoo's base onchange_order_line_ids will update totals

    def write(self, vals):
        res = super().write(vals)
        # Recompute totals if flag is changed, to ensure 0
        if 'is_peminjaman' in vals and vals.get('is_peminjaman'):
            for line in self.order_line:
                line.price_unit = 0.0
                line.taxes_id = False
            self.order_line._onchange_product_id() # Recompute line totals
            self._amount_all() # Recompute order totals
        return res

    def _prepare_invoice(self):
        """ Override to pass borrow flag to vendor bill. """
        invoice_vals = super()._prepare_invoice()
        invoice_vals['is_peminjaman'] = self.is_peminjaman
        return invoice_vals

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_peminjaman_line = fields.Boolean(related='order_id.is_peminjaman', store=True, readonly=False)

    @api.onchange('product_id', 'product_qty', 'price_unit', 'taxes_id')
    def _onchange_price_for_borrow(self):
        """ Set unit price to 0 if it's a borrow transaction. """
        if self.is_peminjaman_line:
            self.price_unit = 0.0
            self.taxes_id = False # Remove taxes as well for 0 price
            # Force recompute of subtotal and order total
            self._onchange_product_id() # This will re-trigger quantity and unit price changes