# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3AccountingBankReconcile(http.Controller):
#     @http.route('/equip3_accounting_bank_reconcile/equip3_accounting_bank_reconcile/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_accounting_bank_reconcile/equip3_accounting_bank_reconcile/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_accounting_bank_reconcile.listing', {
#             'root': '/equip3_accounting_bank_reconcile/equip3_accounting_bank_reconcile',
#             'objects': http.request.env['equip3_accounting_bank_reconcile.equip3_accounting_bank_reconcile'].search([]),
#         })

#     @http.route('/equip3_accounting_bank_reconcile/equip3_accounting_bank_reconcile/objects/<model("equip3_accounting_bank_reconcile.equip3_accounting_bank_reconcile"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_accounting_bank_reconcile.object', {
#             'object': obj
#         })
