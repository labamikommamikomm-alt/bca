# -*- coding: utf-8 -*-
# from odoo import http


# class ExtraPrice(http.Controller):
#     @http.route('/extra_price/extra_price/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/extra_price/extra_price/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('extra_price.listing', {
#             'root': '/extra_price/extra_price',
#             'objects': http.request.env['extra_price.extra_price'].search([]),
#         })

#     @http.route('/extra_price/extra_price/objects/<model("extra_price.extra_price"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('extra_price.object', {
#             'object': obj
#         })
