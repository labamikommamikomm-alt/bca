# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
from odoo.tools.misc import get_lang

class PurchaseOrderLineInherit(models.Model):
    _inherit = 'stock.valuation.layer'
    
    multi_uom_quant = fields.Char(string='Unit Value (Multi UoM)', compute='_multi_uom_compute')
    stored_quant = fields.Char(string='Unit Value (Stored Multi UoM)', default='False')
    
    def _multi_uom_compute(self):
        for record in self:
            qty_string = ''

            product = record.product_id

            if product.multi_uom_enabled:
                
                sale_order = self.env['sale.order'].search([('name','=', record.stock_move_id.origin)])

                purchase_order = self.env['purchase.order'].search([('name','=', record.stock_move_id.origin)])

                if len(sale_order) > 0:
                    for line in sale_order.order_line:
                        qty = 0
                        if line.product_uom.uom_type == 'reference':
                            qty = line.product_uom_qty
                        if line.product_uom.uom_type == 'bigger':
                            qty = line.product_uom_qty * line.product_uom.factor_inv
                        if line.product_uom.uom_type == 'smaller':
                            qty = line.product_uom_qty * line.product_uom.factor
                            
                        if product.id == line.product_id.id and qty == record.stock_move_id.product_uom_qty:
                            qty_string += str(line.product_uom_qty) + ' '+ line.product_uom.name
                            
                if len(purchase_order) > 0:
                    for line in purchase_order.order_line:
                        qty = 0
                        if line.product_uom.uom_type == 'reference':
                            qty = line.product_qty
                        if line.product_uom.uom_type == 'bigger':
                            qty = line.product_qty * line.product_uom.factor_inv
                        if line.product_uom.uom_type == 'smaller':
                            qty = line.product_qty * line.product_uom.factor
                            
                        # raise exceptions.UserError(str(qty) +" = "  + str(record.stock_move_id.product_uom_qty))
                            
                        if product.id == line.product_id.id and qty == record.stock_move_id.product_uom_qty:
                            qty_string += str(line.product_qty) + ' '+ line.product_uom.name

            if qty_string == '':
                qty_string = record.stored_quant
            else:
                record.stored_quant = qty_string
                
            if qty_string == '':
                qty_string = 'False'

            record.multi_uom_quant = qty_string