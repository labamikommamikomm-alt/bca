# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Technical field to hide country specific fields from accounting configuration
    global_taxes = fields.Boolean(string='Enable Global Taxes')

    def set_values(self):
        """employee setting field values"""
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('account.global_taxes', self.global_taxes)
        return res
   
    def get_values(self):
        """employee limit getting field values"""
        res = super(ResConfigSettings, self).get_values()
        value = self.env['ir.config_parameter'].sudo().get_param('account.global_taxes', default=False)

        res.update(
            global_taxes=value
        )
        return res

