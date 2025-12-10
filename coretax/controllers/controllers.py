# -*- coding: utf-8 -*-
# from odoo import http


# class Coretax(http.Controller):
#     @http.route('/coretax/coretax/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/coretax/coretax/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('coretax.listing', {
#             'root': '/coretax/coretax',
#             'objects': http.request.env['coretax.coretax'].search([]),
#         })

#     @http.route('/coretax/coretax/objects/<model("coretax.coretax"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('coretax.object', {
#             'object': obj
#         })
