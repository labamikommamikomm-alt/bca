# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import get_lang
from odoo.exceptions import ValidationError, RedirectWarning, UserError
import logging

_logger = logging.getLogger(__name__)

class ProductLastPriceVendor(models.Model):
    _name = 'product.last.price.vendor'
    _description = 'Last price of a product for a specific vendor'
    _rec_name = 'last_price'
    _sql_constraints = [
        ('product_partner_unique', 'unique(product_id, partner_id)',
         'The combination of product and vendor must be unique!')
    ]

    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Vendor', 
        required=True
    )
    last_price = fields.Float(
        string='Last Price', 
        digits='Product Price', 
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        default=lambda self: self.env.company.currency_id.id
    )

    def init(self):
        """
        Runs the migration function on module update/installation.
        """
        self.env.cr.execute("SELECT count(*) FROM product_last_price_vendor")
        if self.env.cr.fetchone()[0] == 0:
            self._migrate_last_prices()

    def _migrate_last_prices(self):
        """
        Helper method to perform the data migration for purchase last prices.
        """
        _logger.info("Starting historical data migration for product last purchase prices...")
        
        # Taking confirmed and done purchase orders, sorted by date descending.
        purchase_orders = self.env['purchase.order'].search([
            ('state', 'in', ['purchase', 'done'])
        ], order='date_order desc')

        last_prices = {}
        # Iterate through orders (newest first) and then their lines
        for order in purchase_orders:
            for line in order.order_line:
                if not line.product_id or not order.partner_id or line.price_unit <= 0:
                    continue
                
                key = (line.product_id.id, order.partner_id.id)
                # Since we iterate newest orders first, the first time we see a product-vendor
                # combination, it is the most recent price.
                if key not in last_prices:
                    last_prices[key] = line.price_unit

        for key, price in last_prices.items():
            product_id, partner_id = key
            self.create({
                'product_id': product_id,
                'partner_id': partner_id,
                'last_price': price,
            })
        _logger.info("Historical data migration for purchase last prices completed.")



class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"

    prepaid = fields.Boolean(string="Dibayar Dimuka")

    prepaid_bill = fields.Many2one(
        "account.move",
        domain="[('journal_id.type', '=', 'purchase'), ('used_bill', '=', False), ('partner_id', '=', partner_id)]",
    )

    def _bill_confirmation(self):
        # get procurement group
        group = self.env["procurement.group"].search([("name", "=", self.name)])
        group = group[0]
        # get stock picking
        stock_pickings = self.env["stock.picking"].search(
            [
                ("group_id", "=", group.id),
                ("state", "=", "assigned"),
            ]
        )

        # raise UserError(str(len(stock_pickings)))

        # Validate stock
        pickings_to_do = self.env["stock.picking"]
        for picking in stock_pickings:
            pickings_to_do |= picking
            # self.env['stock.immediate.transfer'].with_context(
            #     {
            #         'active_model': 'stock.picking',
            #         'active_ids': picking.id,
            #         'default_pick_ids': [picking.id]
            #     }
            # ).process()
        for picking in pickings_to_do:
            if picking.state == "draft":
                picking.action_confirm()
                if picking.state != "assigned":
                    picking.action_assign()
                    if picking.state != "assigned":
                        raise UserError(
                            _(
                                "Could not reserve all requested products. Please use the 'Mark as Todo' button to handle the reservation manually."
                            )
                        )
            for move in picking.move_lines.filtered(
                lambda m: m.state not in ["done", "cancel"]
            ):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty

        pickings_to_do.with_context(skip_immediate=True).button_validate()

        # Create bill
        res = self.action_create_invoice()

        vendor_bill = self.env["account.move"].search([("id", "=", res["res_id"])])
        vendor_bill = vendor_bill[0]

        vendor_bill.invoice_date = fields.Date.today()
        vendor_bill.action_post()

        if self.prepaid_bill.amount_total < vendor_bill.amount_total:
            # Pay bill
            self.env["account.payment.register"].with_context(
                {"active_model": "account.move", "active_ids": vendor_bill.id}
            ).create(
                {
                    "journal_id": 10,
                    "payment_type": "outbound",
                    "payment_method_id": 2,
                    "amount": self.prepaid_bill.amount_total,
                    "payment_difference_handling": "open",
                }
            ).action_create_payments()
        else:
            # Pay bill
            self.env["account.payment.register"].with_context(
                {"active_model": "account.move", "active_ids": vendor_bill.id}
            ).create(
                {"journal_id": 10, "payment_type": "outbound", "payment_method_id": 2}
            ).action_create_payments()

        self.prepaid_bill.used_bill = True

    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                eff_price = line.price_unit
                if getattr(line, "discount", 0.0):
                    eff_price *= 1 - (line.discount or 0.0) / 100.0
                if getattr(line, "fixed_discount", 0.0):
                    if line.product_qty:
                        eff_price -= line.fixed_discount / line.product_qty
                    else:
                        eff_price -= line.fixed_discount
                if eff_price < 0:
                    eff_price = 0.0
                taxes = line.taxes_id.compute_all(
                    eff_price,
                    order.currency_id,
                    line.product_qty,
                    line.product_id,
                    order.partner_id,
                )
                amount_untaxed += taxes.get("total_excluded", 0.0)
                amount_tax += taxes.get("total_included", 0.0) - taxes.get(
                    "total_excluded", 0.0
                )
            order.update(
                {
                    "amount_untaxed": amount_untaxed,
                    "amount_tax": amount_tax,
                    "amount_total": amount_untaxed + amount_tax,
                }
            )

    def button_confirm(self):
        res = super(PurchaseOrderInherit, self).button_confirm()

        if self.prepaid:
            self._bill_confirmation()
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id_update_prices(self):
        """
        When the vendor is changed, re-evaluate the prices for all
        the purchase order lines based on the new vendor's last prices.
        """
        if self.partner_id and self.order_line:
            for line in self.order_line:
                line.onchange_product_id()


class PurchaseOrderLineInherit(models.Model):
    _inherit = "purchase.order.line"

    product_uom_category_id = fields.Many2one("uom.category")
    discount = fields.Float(string="Discount (%)", default=0.0)
    fixed_discount = fields.Float(string="Fixed Discount", default=0.0)

    def _apply_last_price_logic(self, res):
        """Helper to apply last price logic to onchanges."""
        if self.product_id:
            # Ambil dari harga_terakhir atau standard_price (modal)
            final_price = self.product_id.harga_terakhir or self.product_id.standard_price
            
            self.price_unit = final_price
            
            # Update the returned dict to prevent client-side overwrite
            if isinstance(res, dict) and 'value' in res:
                res['value']['price_unit'] = final_price
        
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = {}
        if hasattr(super(PurchaseOrderLineInherit, self), 'onchange_product_id'):
            res = super(PurchaseOrderLineInherit, self).onchange_product_id()
            
        if not self.product_id:
            return res

        if self.product_id.multi_uom_enabled:
            self.product_uom_category_id = self.product_id.multi_uom_category_id
        else:
            self.product_uom_category_id = self.product_id.uom_id.category_id
            self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        
        return self._apply_last_price_logic(res)

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if hasattr(super(PurchaseOrderLineInherit, self), 'onchange_product_uom'):
            res = super(PurchaseOrderLineInherit, self).onchange_product_uom()
        return self._apply_last_price_logic(res)

    @api.depends("product_qty", "price_unit", "taxes_id", "discount", "fixed_discount")
    def _compute_amount(self):
        for line in self:
            eff_price = line.price_unit

            if line.discount:
                eff_price = eff_price * (1 - (line.discount or 0.0) / 100.0)

            if line.fixed_discount:
                if line.product_qty:
                    eff_price -= line.fixed_discount / line.product_qty
                else:
                    eff_price -= line.fixed_discount

            if eff_price < 0:
                eff_price = 0.0

            taxes = line.taxes_id.compute_all(
                eff_price,
                line.order_id.currency_id,
                line.product_qty,
                line.product_id,
                line.order_id.partner_id,
            )
            line.update(
                {
                    "price_subtotal": taxes["total_excluded"],
                    "price_total": taxes["total_included"],
                }
            )

