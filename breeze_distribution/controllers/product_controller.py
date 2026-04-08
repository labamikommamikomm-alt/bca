# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class ProductController(http.Controller):
    @http.route('/breeze_distribution/get/product', csrf=False, auth='user', methods=['POST'], type='json')
    def get_product(self, **kw):
        res = []
        
        offset = (kw['page'] - 1) * 10
        step = kw['step']
        query = ''
        
        if 'query' in kw:
            query = kw['query']
        
        products = request.env['product.product'].search([
            ('sale_ok', '=', True),
            ('name', 'ilike', query )
        ], offset=offset, limit=step)
        
        for product in products:
            
            multi_uom = []
            
            for uom_qty in product.multi_uom_ids:
                uom = {
                    'id': uom_qty.id,
                    'warehouse':{
                        'id': uom_qty.warehouse_id.id,
                        'name': uom_qty.warehouse_id.name,
                    },
                    'product_uom_category': {
                        'id': uom_qty.product_uom_category_id.id,
                        'name': uom_qty.product_uom_category_id.name,
                    },
                    'uom': {
                        'id': uom_qty.uom_id.id,
                        'name': uom_qty.uom_id.name,
                        'uom_type': uom_qty.uom_id.uom_type,
                        'factor': uom_qty.uom_id.factor,
                        'factor_inv': uom_qty.uom_id.factor_inv,
                    },
                    'qty': uom_qty.qty
                }
                
                multi_uom.append(uom)
            
            product_object = {
                'id': product.id,
                'name': product.name,
                'uom': {
                    'id': product.uom_id.id,
                    'name': product.uom_id.name,
                    'uom_type': product.uom_id.uom_type,
                    'factor': product.uom_id.factor,
                    'factor_inv': product.uom_id.factor_inv,
                    'category': {
                        'id': product.uom_id.category_id.id,
                        'name': product.uom_id.category_id.name,
                    }
                },
                'qty_available': product.qty_available,
                'multi_uom_enabled': product.multi_uom_enabled,
                'multi_uom_category' : {
                    'id': product.multi_uom_category_id.id,
                    'name': product.multi_uom_category_id.name,
                }, 
                'multi_qty': multi_uom,
                'list_price': product.list_price,
            }
            
            
            res.append(product_object)
            
        return res