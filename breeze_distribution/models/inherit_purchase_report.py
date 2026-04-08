import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class inheritPurchaseReport(models.Model):
    _inherit = "purchase.report"

    price_unit = fields.Float(string="Price Unit")

    def _select(self):
        return super(inheritPurchaseReport, self)._select() + ", l.price_unit"

    def _group_by(self):
        return super(inheritPurchaseReport, self)._group_by() + ", l.price_unit"
