# -*- coding: utf-8 -*-
# from odoo import http


# class Peminjaman(http.Controller):
#     @http.route('/peminjaman/peminjaman/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/peminjaman/peminjaman/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('peminjaman.listing', {
#             'root': '/peminjaman/peminjaman',
#             'objects': http.request.env['peminjaman.peminjaman'].search([]),
#         })

#     @http.route('/peminjaman/peminjaman/objects/<model("peminjaman.peminjaman"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('peminjaman.object', {
#             'object': obj
#         })
