# -*- coding: utf-8 -*-
# from odoo import http

# class Xendit(http.Controller):
#     @http.route('/xendit/xendit/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/xendit/xendit/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('xendit.listing', {
#             'root': '/xendit/xendit',
#             'objects': http.request.env['xendit.xendit'].search([]),
#         })

#     @http.route('/xendit/xendit/objects/<model("xendit.xendit"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('xendit.object', {
#             'object': obj
#         })
