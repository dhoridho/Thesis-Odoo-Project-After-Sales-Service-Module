# -*- coding: utf-8 -*-
# from odoo import http


# class AgreementModifier(http.Controller):
#     @http.route('/agreement_modifier/agreement_modifier/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/agreement_modifier/agreement_modifier/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('agreement_modifier.listing', {
#             'root': '/agreement_modifier/agreement_modifier',
#             'objects': http.request.env['agreement_modifier.agreement_modifier'].search([]),
#         })

#     @http.route('/agreement_modifier/agreement_modifier/objects/<model("agreement_modifier.agreement_modifier"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('agreement_modifier.object', {
#             'object': obj
#         })
