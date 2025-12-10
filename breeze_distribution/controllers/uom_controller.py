# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class UOMController(http.Controller):
    @http.route('/breeze_distribution/get/uom', csrf=False, auth='user', methods=['POST'], type='json')
    def get_uom(self, **kw):
        # User id validation
        res = []
        
        categories = request.env['uom.category'].search([])
        
        for category in categories:
            category_object = {
                'id': category.id,
                'name': category.name,
                'uoms': [] 
            }
            
            uoms = request.env['uom.uom'].search([
                ('category_id', '=', category.id),
                ('active', '=', True),
            ])
            
            for uom in uoms:
                uom_object = {
                    'id': uom.id,
                    'name': uom.name,
                    'type': uom.uom_type,
                    'factor': uom.factor,
                    'factor_inv': uom.factor_inv,
                }
                
                category_object['uoms'].append(uom_object)
            
            res.append(category_object)
        
        return res