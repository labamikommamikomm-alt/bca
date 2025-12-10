# your_module_name/data/migration.py

from odoo import api, SUPERUSER_ID, tools

@tools.post_init_hook
def migrate_last_prices(cr, registry):
    """
    Function to populate the 'product.last.price.customer' model
    based on the most recent completed sales orders.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Mengambil semua sale order line yang sudah divalidasi dan diurutkan
    # berdasarkan tanggal order secara descending.
    # Ini memastikan kita mengambil harga dari transaksi paling baru.
    sale_lines = env['sale.order.line'].search([
        ('state', 'in', ['sale', 'done']),
        ('price_unit', '>', 0)
    ], order='order_id.date_order desc')

    last_prices = {}
    
    # Iterasi melalui sale lines dari yang paling baru
    for line in sale_lines:
        product = line.product_id
        customer = line.order_id.partner_id

        if not product or not customer:
            continue

        key = (product.id, customer.id)
        
        # Jika kombinasi produk dan pelanggan belum ada di dict,
        # simpan harga dan lanjut ke transaksi sebelumnya.
        if key not in last_prices:
            last_prices[key] = line.price_unit

    _logger = env['ir.module.module']._logger
    _logger.info("Migrating historical last prices for products and customers...")
    
    # Buat records di model product.last.price.customer
    for key, price in last_prices.items():
        product_id, partner_id = key
        env['product.last.price.customer'].create({
            'product_id': product_id,
            'partner_id': partner_id,
            'last_price': price,
        })

    _logger.info("Migration of historical last prices completed.")