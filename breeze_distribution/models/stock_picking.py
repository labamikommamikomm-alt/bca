# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, RedirectWarning, UserError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'
    
    # --- Custom Functions from other modules/logic ---
    
    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        
        if res is True:
            self.apply_multi_stock_purchase()
            self.apply_multi_stock_sale()
        return res
    
    def apply_multi_stock_purchase(self):
        po = self.env['purchase.order'].search([('name', '=', self.origin)])
        
        if not po:
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
        
        if not sale:
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

    # --- Scheduled Date Override Logic ---
    
    @api.model
    def create(self, vals):
        # 1. Store and remove scheduled_date from vals to avoid initial conflict
        scheduled_date_val = vals.pop('scheduled_date', False)

        # 2. Let Odoo create the picking record
        record = super(StockPickingInherit, self).create(vals)

        # 3. Enforce the scheduled_date immediately after creation
        if record.picking_type_code == 'outgoing':
            _logger
            # Overwrite the date calculated by SO/Lead Time with the current time (Naive Datetime)
            record.write({'scheduled_date': fields.Datetime.now()})
        _logger.info(fields.Datetime.now())
        return record
        
    def write(self, vals):
        # This function runs when an existing record is saved.
        
        # Check 1: Is this an outgoing delivery order?
        is_outgoing_transfer = any(picking.picking_type_code == 'outgoing' for picking in self)
        
        if is_outgoing_transfer and 'scheduled_date' in vals:
            # Check 2: Check if any record in the current set is in 'done' or 'cancel' state.
            # We ONLY want to overwrite the date if ALL records are NOT done/cancelled.
            
            # Find transfers that are still editable (not done or cancelled)
            editable_transfers = self.filtered(lambda p: p.state not in ('done', 'cancel'))
            
            # If the user is trying to update a date on an editable outgoing transfer:
            if editable_transfers:
                # Force scheduled_date to the current time for the editable transfers
                # This ensures the date is refreshed every time it's saved.
                
                # Note: The logic below is risky as it might be overwritten by other modules.
                # The safest way is to ensure Odoo's core validation is met.
                
                # Since we cannot selectively update 'vals' based on 'self' records, 
                # we only proceed if we know the user intends to change the scheduled_date
                # AND at least one record is editable.
                
                # We can't safely change vals here without potentially violating 
                # the "done/cancel" rule in the super call if the user is changing 
                # something else (e.g., location) and the date is also included in vals.
                
                # Let's simplify and assume if scheduled_date is in vals, we enforce the current time, 
                # but only on editable records. Since we can't do this inside 'write' before 'super', 
                # the user needs to manually set the time OR we only enforce on create.
                
                # REVISI: Hapus logika enforcement di write. 
                # Enforcement di write sering melanggar validasi Odoo (seperti yang kamu alami).
                # Kita hanya akan enforce pada saat CREATE (saat DO baru dibuat).
                
                # Jika kamu ingin *hanya* mencegah error "You cannot change...",
                # kamu harus memastikan `scheduled_date` tidak dipaksa di `vals` 
                # jika `self` mengandung record yang sudah `done` atau `cancel`.
                
                # Karena tujuan utama adalah *Scheduled Date* adalah *Creation Date*, 
                # kita hanya perlu mengandalkan logika di `create` yang jauh lebih aman.
                pass 
            
        return super(StockPickingInherit, self).write(vals)