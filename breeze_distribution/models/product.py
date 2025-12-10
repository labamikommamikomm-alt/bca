# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, RedirectWarning, UserError


class ProductInherit(models.Model):
    _inherit = 'product.template'
    
    multi_uom_enabled = fields.Boolean(string='Multi UoM', default=False)
    
    multi_uom_ids = fields.One2many('uom.multi', 'product_id' , string='Multi UoM')
    
    multi_uom_category_id = fields.Many2one('uom.category', string='UoM Category')

    kadaluarsa = fields.Date(string="Kadaluarsa")
    
    harga_terakhir = fields.Float(string='Harga Pembelian Terakhir', compute='_compute_harga_akhir')
    
    def write(self, vals):
        res = super(ProductInherit, self).write(vals)
        self.syncQty()
        return res
    
    @api.depends('seller_ids.price')
    def _compute_harga_akhir(self):
        for rec in self:
            # Cek apakah produk ini memiliki data pemasok (seller)
            if rec.seller_ids:
                # Jika ada, ambil harga dari pemasok terakhir di daftar
                rec.harga_terakhir = rec.seller_ids[-1].price
            else:
                # Jika tidak ada pemasok, atur harga terakhir menjadi 0
                rec.harga_terakhir = 0.0
         
            
            
    @api.onchange('multi_uom_category_id')
    def change_default_uom(self):
        # raise ValidationError('boop')
        # for line in self:
        if self.multi_uom_enabled:
            
            base_uom = self.env['uom.uom'].search([('uom_type', '=', 'reference'), ('category_id','=', self.multi_uom_category_id.id)])
            
            if len(base_uom) < 1:
                return 
            
            base_uom = base_uom[0]
            
            self.uom_id = base_uom.id
            self.uom_po_id = base_uom.id
    
    def syncQty(self):
        
        if not self.multi_uom_enabled:
            return
        
        product = self.product_variant_id
        
        totalQty = {}
        
        for quant in product.stock_quant_ids:
            if quant.location_id.id not in totalQty.keys():
                totalQty[quant.location_id.id] = 0
            
        for uom in product.multi_uom_ids:
            location = uom.warehouse_id.lot_stock_id
            if location.id not in totalQty.keys():
                totalQty[location.id] = 0
            
            if uom.uom_id.uom_type == 'reference':
                totalQty[location.id] += uom.qty
            elif uom.uom_id.uom_type == 'bigger':
                totalQty[location.id] += uom.qty * uom.uom_id.factor_inv
            elif uom.uom_id.uom_type == 'smaller':
                totalQty[location.id] += uom.qty / uom.uom_id.factor
        
        # delete quants
        # for quant in product.stock_quant_ids:
        #     quant.sudo().unlink()
        
        for locationId in totalQty.keys():
            quant = self.env['stock.quant'].sudo()
            
            location = self.env['stock.location'].search([('id', '=', locationId)])[0]
            
            updateQty = totalQty[locationId] - quant._get_available_quantity(product, location)
            
            quant._update_available_quantity(product, location, updateQty)
            # quant.create({
            #     'location_id': locationId,
            #     'product_id': product.id,
            #     'quantity': totalQty[locationId]
            # })

class MultiUom(models.Model):
    _name = 'uom.multi'
    _description = 'Multiple UoM'
    
    product_id = fields.Many2one('product.template', string='Product')
    uom_id = fields.Many2one('uom.uom', string='UoM', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.multi_uom_category_id')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    qty = fields.Integer(string='Quantity')