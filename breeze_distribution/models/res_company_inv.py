from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Field baru untuk menyimpan kode cabang/prefix invoice (misal: A, B, JKT)
    invoice_branch_prefix = fields.Char(
        string='Invoice Branch Prefix',
        help="Prefix karakter yang akan digunakan dalam penamaan faktur pajak kustom (misal: 'A').",
        default='A',
        required=True
    )
