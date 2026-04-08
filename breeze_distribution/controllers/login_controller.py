# -*- coding: utf-8 -*-
from odoo import http, _, exceptions
from odoo.http import request


class LoginController(http.Controller):
    @http.route('/breeze_distribution/login', csrf=False, auth='public', methods=['POST'], type='json')
    def login(self, **kw):
        # Validation
        try:
            login = kw["login"]
        except KeyError:
            raise exceptions.ValidationError(message='`login` is required.')

        try:
            password = kw["password"]
        except KeyError:
            raise exceptions.ValidationError(message='`password` is required.')

        try:
            db = kw["db"]
        except KeyError:
            raise exceptions.ValidationError(message='`db` is required.')

        # Auth user
        http.request.session.authenticate(db, login, password)
        # Session info
        res = request.env['ir.http'].session_info()

        return res