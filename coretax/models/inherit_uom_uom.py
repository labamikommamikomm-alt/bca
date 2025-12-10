# l10n_id_coretax/models/uom_uom.py
from odoo import models, fields

class UomUom(models.Model):
    _inherit = 'uom.uom'

    kode_satuan = fields.Char(string='Kode Satuan Coretax')