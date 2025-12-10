import json
from odoo import models, fields, api, exceptions,_
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError


class InheritResCompany(models.Model):
    _inherit = 'res.company'

    nama_bank = fields.Char(string="Nama Bank 1")
    rek_bank = fields.Char(string="Rekening Bank 1")
    atas_nama = fields.Char(string="Atas Nama 1")
    nama_bank2 = fields.Char(string="Nama Bank 2")
    rek_bank2 = fields.Char(string="Rekening Bank 2")
    atas_nama2 = fields.Char(string="Atas Nama 2")
