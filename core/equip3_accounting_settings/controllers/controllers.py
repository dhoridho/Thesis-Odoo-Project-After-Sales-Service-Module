# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3AccountingSettings(http.Controller):
#     @http.route('/equip3_accounting_settings/equip3_accounting_settings/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_accounting_settings/equip3_accounting_settings/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_accounting_settings.listing', {
#             'root': '/equip3_accounting_settings/equip3_accounting_settings',
#             'objects': http.request.env['equip3_accounting_settings.equip3_accounting_settings'].search([]),
#         })

#     @http.route('/equip3_accounting_settings/equip3_accounting_settings/objects/<model("equip3_accounting_settings.equip3_accounting_settings"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_accounting_settings.object', {
#             'object': obj
#         })
