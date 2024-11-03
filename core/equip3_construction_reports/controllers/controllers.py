# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3ConstructionReports(http.Controller):
#     @http.route('/equip3_construction_reports/equip3_construction_reports/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_construction_reports/equip3_construction_reports/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_construction_reports.listing', {
#             'root': '/equip3_construction_reports/equip3_construction_reports',
#             'objects': http.request.env['equip3_construction_reports.equip3_construction_reports'].search([]),
#         })

#     @http.route('/equip3_construction_reports/equip3_construction_reports/objects/<model("equip3_construction_reports.equip3_construction_reports"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_construction_reports.object', {
#             'object': obj
#         })
