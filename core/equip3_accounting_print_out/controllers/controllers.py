# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3AccountingPrintOut(http.Controller):
#     @http.route('/equip3_accounting_print_out/equip3_accounting_print_out/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_accounting_print_out/equip3_accounting_print_out/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_accounting_print_out.listing', {
#             'root': '/equip3_accounting_print_out/equip3_accounting_print_out',
#             'objects': http.request.env['equip3_accounting_print_out.equip3_accounting_print_out'].search([]),
#         })

#     @http.route('/equip3_accounting_print_out/equip3_accounting_print_out/objects/<model("equip3_accounting_print_out.equip3_accounting_print_out"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_accounting_print_out.object', {
#             'object': obj
#         })
