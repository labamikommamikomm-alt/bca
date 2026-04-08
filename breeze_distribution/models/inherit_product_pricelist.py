import json
from odoo import models, fields, api, exceptions,_
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError

class inherit_product_pricelist(models.Model):
    _inherit = 'product.pricelist.item'

    uom = fields.Many2one('uom.uom', string = "UoM")

    
