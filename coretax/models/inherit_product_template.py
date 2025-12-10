# l10n_id_coretax/models/product_template.py
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barang_jasa = fields.Selection([
        ('A', 'Barang'), ('B', 'Jasa')
    ], string='Tipe (Barang/Jasa)', default='A', help="Tipe untuk ekspor Coretax.")