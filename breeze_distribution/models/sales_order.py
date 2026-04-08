# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductLastPriceCustomer(models.Model):
    _name = 'product.last.price.customer'
    _description = 'Last price of a product for a specific customer'
    _rec_name = 'last_price'
    _sql_constraints = [
        ('product_partner_unique', 'unique(product_id, partner_id)',
         'The combination of product and customer must be unique!')
    ]

    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Customer', 
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
        # Cek apakah tabel sudah ada dan kosong
        # Ini mencegah skrip berjalan berulang kali pada setiap update minor
        self.env.cr.execute("SELECT count(*) FROM product_last_price_customer")
        if self.env.cr.fetchone()[0] == 0:
            self._migrate_last_prices()

    def _migrate_last_prices(self):
        """
        Helper method to perform the data migration.
        """
        _logger.info("Starting historical data migration for product last prices...")
        
        # Langkah 1: Ambil ID Sales Order yang sudah divalidasi dan urutkan
        # berdasarkan tanggal order secara descending.
        # Sorting now happens on the sale.order model.
        sale_orders = self.env['sale.order'].search([
            ('state', 'in', ['sale', 'done'])
        ], order='date_order desc')

        # Langkah 2: Gunakan ID dari sales orders untuk mencari sales order lines.
        # Kita perlu mencari lines yang terkait dengan order_id yang sudah diurutkan.
        sale_lines = self.env['sale.order.line'].search([
            ('order_id', 'in', sale_orders.ids),
            ('price_unit', '>', 0)
        ])

        last_prices = {}
        for line in sale_lines:
            product = line.product_id
            customer = line.order_id.partner_id

            if not product or not customer:
                continue

            key = (product.id, customer.id)
            
            # Logika ini akan berjalan dari lines yang paling baru karena
            # `sale_orders` sudah diurutkan dari yang paling baru.
            if key not in last_prices:
                last_prices[key] = line.price_unit

        for key, price in last_prices.items():
            product_id, partner_id = key
            self.create({
                'product_id': product_id,
                'partner_id': partner_id,
                'last_price': price,
            })
        _logger.info("Historical data migration completed.")

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_update_prices(self):
        """
        When the customer is changed, re-evaluate the prices for all
        the sale order lines based on the new customer's last prices.
        """
        if self.partner_id and self.order_line:
            for line in self.order_line:
                # Call the onchange logic directly for each line
                line._onchange_product_id_set_last_price()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    
    def _get_display_price(self, product):
        """
        Menghitung harga tampilan untuk sale order line.
        Memprioritaskan harga terakhir dari transaksi pelanggan,
        kemudian baru memeriksa daftar harga (pricelist).
        """
        _logger.info("Calculating display price for product %s and customer %s",
                      product.id, self.order_id.partner_id.id)
        # Langkah 1: Cari harga terakhir berdasarkan produk dan pelanggan.
        last_price_record = self.env['product.last.price.customer'].search([
            ('product_id', '=', product.id),
            ('partner_id', '=', self.order_id.partner_id.id)
        ], limit=1)

        if last_price_record:
            # Jika harga terakhir ditemukan, kembalikan harga tersebut.
            return last_price_record.last_price

        # Langkah 2: Jika tidak ada harga terakhir, gunakan logika super.
        # Logika ini akan memeriksa pricelist atau harga default produk.
        res = super(SaleOrderLine, self)._get_display_price(product)
        return res


    
    def _update_last_price_for_customer(self):
        """
        Helper method to update or create the last price record
        for the current sale order line's product and customer.
        """
        if self.product_id and self.order_id.partner_id:
            last_price_record = self.env['product.last.price.customer'].search([
                ('product_id', '=', self.product_id.id),
                ('partner_id', '=', self.order_id.partner_id.id)
            ], limit=1)

            if last_price_record:
                last_price_record.write({'last_price': self.price_unit})
            else:
                self.env['product.last.price.customer'].create({
                    'product_id': self.product_id.id,
                    'partner_id': self.order_id.partner_id.id,
                    'last_price': self.price_unit,
                })

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create to update the last price per customer after creation.
        """
        records = super(SaleOrderLine, self).create(vals_list)
        for record in records:
            record._update_last_price_for_customer()
        return records

    def write(self, vals):
        """
        Overrides write to update the last price per customer after modification.
        """
        res = super(SaleOrderLine, self).write(vals)
        for record in self:
            if 'price_unit' in vals:
                record._update_last_price_for_customer()
        return res

    def unlink(self):
        """
        Handles the deletion of a sale order line.
        This method is kept for completeness but no specific action is taken
        on the last price table on deletion, as it should reflect the last
        successful transaction.
        """
        return super(SaleOrderLine, self).unlink()