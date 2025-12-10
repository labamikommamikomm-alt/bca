# -*- coding: utf-8 -*-
from odoo import http, _, exceptions, fields
from odoo.http import request
from datetime import datetime, timedelta

class SaleOrderController(http.Controller):
    @http.route('/breeze_distribution/get/sale/order', csrf=False, auth='user', methods=['POST'], type='json')
    def get_sale_order(self, **kw):
        user = request.env.user

        params = [('user_id', '=', user.id)]
        if (kw['today']):
            startDay = fields.Datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
            nextDay = fields.Datetime.today().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            params = [('user_id', '=', user.id), ('date_order', '>=', startDay), ('date_order', '<=', nextDay)]
        
        sales_orders = request.env['sale.order'].search(params, order='date_order desc')
        
        res = []
        
        for sale in sales_orders:
            order = {
                'id': sale.id,
                'name': sale.name,
                'state': sale.state,
                'date_order': sale.date_order,
                'salesperson': {
                    'id' : sale.user_id.id,
                    'name' : sale.user_id.name,
                },
                'customer': {
                    'id' : sale.partner_id.id,
                    'name' : sale.partner_id.name,
                    'street': sale.partner_id.street,
                    'street2' : sale.partner_id.street2,
                    'city': sale.partner_id.city 
                },
                'amount_total': sale.amount_total,
                'order_line': [],
            }
            
            for line in sale.order_line:
                order_line = {
                    'product': {
                        'id': line.product_id.id,
                        'name': line.product_id.name
                    },
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': {
                        'id': line.product_uom.id,
                        'name': line.product_uom.name
                    },
                    'discount': line.discount,
                    'price_subtotal': line.price_subtotal,
                    'price_tax': line.price_tax,
                    'price_total': line.price_total,
                    'price_unit': line.price_unit
                }
                
                order['order_line'].append(order_line)
            
            res.append(order)
            
        return res
    
    
    @http.route('/breeze_distribution/create/sale/order', csrf=False, auth='user', methods=['POST'], type='json')
    def create_sale_order(self, **kw):
        
        # !!!Required!!!
        # date_order
        # partner_id
        # lines
        
        # partner id validation
        if 'partner_id' not in kw.keys():
            raise exceptions.ValidationError(message='`partner_id` is required.')
        
        partner = request.env['res.partner'].search([('id', '=', kw['partner_id'])])
        
        if len(partner) < 1:
            raise exceptions.ValidationError(message='partner not found')
        
        partner = partner[0]
        
        # order_lines validation
        if 'order_lines' not in kw.keys():
            raise exceptions.ValidationError(message='`order_lines` is required.')
        
        order_lines = kw['order_lines']
        
        lines = []
        
        for order_line in order_lines:
            product = request.env['product.product'].search([('id', '=', order_line['product_id'])])
            
            if len(product) < 1:
                raise exceptions.ValidationError(message='product id '+ str(order_line['product_id']) +' not found.')
            
            product = product[0]
            uom = request.env['uom.uom'].search([('id', '=', order_line['product_uom'])])

            if len(uom) < 1:
                raise exceptions.ValidationError(message='uom id '+ str(order_line['uom_id']) +' not found.')
            uom = uom[0]
            
            price = 0
            
            if(product.multi_uom_enabled):

                if uom.uom_type == 'reference':
                    price = product.list_price

                if uom.uom_type == 'bigger':
                    price = product.list_price * uom.factor_inv

                if uom.uom_type == 'smaller':
                    price = product.list_price / uom.factor
            else:
                reference_uom = request.env['uom.uom'].search([('category_id', '=', uom.category_id.id), ('uom_type', '=', 'reference')])
                reference_uom = reference_uom[0]
                
                product_uom = product.uom_id
                
                reference_price = 0
                
                if product_uom.uom_type == 'reference':
                    reference_price = product.list_price

                if product_uom.uom_type == 'bigger':
                    reference_price = product.list_price / uom.factor_inv

                if product_uom.uom_type == 'smaller':
                    reference_price = product.list_price * uom.factor
                    
                price = reference_price * uom.factor_inv
                
            line = [0, 0, {
                'product_id': product.id,
                'name': product.name,
                'price_unit': price,
                'product_uom_qty': order_line['product_uom_qty'],
                'product_uom': order_line['product_uom'],
            }]
            
            lines.append(line)
        
        orderVals = {
            'date_order': datetime.now(),
            'partner_id': partner.id,
            'order_line': lines,
            'state': 'sale'
        }
        
        request.env['sale.order'].create(orderVals)
        
        
        return {
            'success': True,
            'message': 'sales order berhasil dibuat'
        }