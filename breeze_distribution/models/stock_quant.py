# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class StockPickingInherit(models.Model):
    _inherit = 'stock.quant'
    
    multi_uom_quant = fields.Char(string='Qty (Multi UoM)', compute='_multi_uom_compute')
    
    def _multi_uom_compute(self):
        qty_string = ''
        
        product = self.product_id
        location = self.location_id
        
        if product.multi_uom_enabled:
            smaller_uom = self.env['uom.uom'].search([
                ('category_id', '=', product.multi_uom_category_id.id),
                ('uom_type', '=', 'smaller'),
            ], order='factor desc')
            
            reference_uom = self.env['uom.uom'].search([
                ('category_id', '=', product.multi_uom_category_id.id),
                ('uom_type', '=', 'reference'),
            ])
            
            bigger_uom = self.env['uom.uom'].search([
                ('category_id', '=', product.multi_uom_category_id.id),
                ('uom_type', '=', 'bigger'),
            ], order='factor_inv asc')
            
            coma = ''
            for uom_stock in product.multi_uom_ids:
                if uom_stock.warehouse_id.lot_stock_id.id == location.id:
                    for uom in smaller_uom:
                        if uom_stock.uom_id.id == uom.id:
                            qty_string += coma+str(uom_stock.qty) +' '+uom_stock.uom_id.name
                            coma = ', '
                                
                    for uom in reference_uom:
                        if uom_stock.uom_id.id == uom.id:
                            qty_string += coma+str(uom_stock.qty) +' '+uom_stock.uom_id.name
                            coma = ', '
                                
                    for uom in bigger_uom:
                        if uom_stock.uom_id.id == uom.id:
                            qty_string += coma+str(uom_stock.qty) +' '+uom_stock.uom_id.name
                            coma = ', '
        if qty_string == '':
            qty_string = 'False'
        
        
        self.multi_uom_quant = qty_string
                            