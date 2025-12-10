from odoo import fields, models


class inheritSaleReport(models.Model):
    _inherit = 'sale.report'

    price_unit = fields.Float('Price Unit')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['price_unit'] = ", l.price_unit as price_unit"
        groupby += ', l.price_unit'
        return super(inheritSaleReport, self)._query(with_clause, fields, groupby, from_clause)
