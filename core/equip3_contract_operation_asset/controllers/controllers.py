# -*- coding: utf-8 -*-
# from odoo import http


# class AgreementModifierAsset(http.Controller):
#     @http.route('/agreement_modifier_asset/agreement_modifier_asset/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/agreement_modifier_asset/agreement_modifier_asset/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('agreement_modifier_asset.listing', {
#             'root': '/agreement_modifier_asset/agreement_modifier_asset',
#             'objects': http.request.env['agreement_modifier_asset.agreement_modifier_asset'].search([]),
#         })

#     @http.route('/agreement_modifier_asset/agreement_modifier_asset/objects/<model("agreement_modifier_asset.agreement_modifier_asset"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('agreement_modifier_asset.object', {
#             'object': obj
#         })
