# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'
    
    
    # Fuck, idk what to do
    # Basically adding a new func on old one
    # Dunno what to do anymore
    
    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        
        if res == True:
            self.apply_multi_stock_purchase()
            self.apply_multi_stock_sale()
        return res
    
    def apply_multi_stock_purchase(self):
        po = self.env['purchase.order'].search([('name', '=', self.origin)])
        
        if(len(po) < 1):
            return
        
        po = po[0]
        
        for line in po.order_line:
            product = line.product_id
            
            if product.multi_uom_enabled:
                for uom in product.multi_uom_ids:
                    location = self.location_dest_id
                    
                    warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', location.id)])
                    
                    if uom.warehouse_id.id == warehouse.id and uom.uom_id.id == line.product_uom.id:
                        newQty = uom.qty + line.product_qty
                        
                        uom.write({
                            'qty': newQty
                        })
                self.syncQty(product)
        
    def apply_multi_stock_sale(self):
        sale = self.env['sale.order'].search([('name', '=', self.origin)])
        
        if(len(sale) < 1):
            return
        
        sale = sale[0]
        
        for line in sale.order_line:
            product = line.product_id
            
            if product.multi_uom_enabled:
                for uom in product.multi_uom_ids:
                    location = self.location_id
                    
                    warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', location.id)])
                    
                    if uom.warehouse_id.id == warehouse.id and uom.uom_id.id == line.product_uom.id:
                        newQty = uom.qty - line.product_uom_qty
                        
                        # raise ValidationError(str(newQty))
                        
                        uom.write({
                            'qty': newQty
                        })
                product.syncQty()
    
    def syncQty(self, product):
        totalQty = {}
        
        for quant in product.stock_quant_ids:
            if quant.location_id.id not in totalQty.keys():
                totalQty[quant.location_id.id] = 0
            
        for uom in product.multi_uom_ids:
            location = uom.warehouse_id.lot_stock_id
            
            if uom.uom_id.uom_type == 'reference':
                totalQty[location.id] += uom.qty
            elif uom.uom_id.uom_type == 'bigger':
                totalQty[location.id] += uom.qty * uom.uom_id.factor_inv
            elif uom.uom_id.uom_type == 'smaller':
                totalQty[location.id] += uom.qty / uom.uom_id.factor
        
        # delete quants
        for quant in product.stock_quant_ids:
            quant.sudo().unlink()
        
        for locationId in totalQty.keys():
            quant = self.env['stock.quant'].sudo()
            
            quant.create({
                'location_id': locationId,
                'product_id': product.id,
                'quantity': totalQty[locationId]
            })
    
    def check_sales(self):
        sales = []
        sale = self.env['sale.order'].search([('name', '=', self.origin)])
        for record in sale:
            if record[0].team_id:
              sales.append(record[0].team_id.name)
            else:
              sales.append("-")
        return ''.join(sales)
        