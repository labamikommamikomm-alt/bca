# -*- coding: utf-8 -*-
# from odoo import http


# class BreezeDistribution(http.Controller):
#     @http.route('/breeze_distribution/breeze_distribution/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/breeze_distribution/breeze_distribution/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('breeze_distribution.listing', {
#             'root': '/breeze_distribution/breeze_distribution',
#             'objects': http.request.env['breeze_distribution.breeze_distribution'].search([]),
#         })

#     @http.route('/breeze_distribution/breeze_distribution/objects/<model("breeze_distribution.breeze_distribution"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('breeze_distribution.object', {
#             'object': obj
#         })
