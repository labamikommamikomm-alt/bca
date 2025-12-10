from odoo import models, fields, api
from odoo.tools.misc import get_lang

class InheritEmployee(models.Model):
    _inherit = 'hr.employee'

    rekap_ids = fields.One2many('breeze_distribution.rekap_titipan', 'employee_id', string='Rekap Titipan')
