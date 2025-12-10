from odoo import _, api, fields, models


class inheritSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    date_purchase = fields.Date(string='Tanggal Pembelian', 
                    default=lambda self: fields.Date.today())
    
