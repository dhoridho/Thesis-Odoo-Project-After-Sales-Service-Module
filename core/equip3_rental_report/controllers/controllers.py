# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3RentalReport(http.Controller):
#     @http.route('/equip3_rental_report/equip3_rental_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_rental_report/equip3_rental_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_rental_report.listing', {
#             'root': '/equip3_rental_report/equip3_rental_report',
#             'objects': http.request.env['equip3_rental_report.equip3_rental_report'].search([]),
#         })

#     @http.route('/equip3_rental_report/equip3_rental_report/objects/<model("equip3_rental_report.equip3_rental_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_rental_report.object', {
#             'object': obj
#         })
