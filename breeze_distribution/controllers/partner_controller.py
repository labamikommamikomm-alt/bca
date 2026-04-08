# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class PartnerController(http.Controller):
    @http.route('/breeze_distribution/get/partner', csrf=False, auth='user', methods=['POST'], type='json')
    def get_partner(self, **kw):
        res = []
        
        partners = request.env['res.partner'].search([('customer_rank','>', 0)])
        
        for partner in partners:
                        
            street = ''
            
            if(partner.street):
                street += partner.street
                
            if(partner.street2):
                street += ' ' + partner.street2
            
            partner_obj = {
                'id': partner.id,
                'name': partner.name,
                'street': street
            }
            
            res.append(partner_obj)
            
        return res