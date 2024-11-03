# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3EinvoiceIntegrationMy(http.Controller):
#     @http.route('/equip3_einvoice_integration_my/equip3_einvoice_integration_my/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_einvoice_integration_my/equip3_einvoice_integration_my/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_einvoice_integration_my.listing', {
#             'root': '/equip3_einvoice_integration_my/equip3_einvoice_integration_my',
#             'objects': http.request.env['equip3_einvoice_integration_my.equip3_einvoice_integration_my'].search([]),
#         })

#     @http.route('/equip3_einvoice_integration_my/equip3_einvoice_integration_my/objects/<model("equip3_einvoice_integration_my.equip3_einvoice_integration_my"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_einvoice_integration_my.object', {
#             'object': obj
#         })
