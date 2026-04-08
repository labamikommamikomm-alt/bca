# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "account.payment.register"
    
    gtax_line_ids = fields.One2many('account.payment.register.line', 'payment_register_id', string='')

    # @api.model
    # def _default_product_id(self):
    #     product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
    #     return self.env['product.product'].browse(int(product_id)).exists()
    
    @api.model
    def _default_lines(self):
        self._default_product_id()
    
    

class SaleAdvancePaymentInvLine(models.TransientModel):
    _name = "account.payment.register.line"
    
    payment_register_id = fields.Many2one('account.payment.register.line',string='Payment Register')
    account = fields.Many2one('breeze_distribution.global_tax',string='Akun Pajak')
    amount = fields.Monetary(string='Jumlah')