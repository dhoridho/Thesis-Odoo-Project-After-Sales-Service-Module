# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3AssetFmsReport(http.Controller):
#     @http.route('/equip3_asset_fms_report/equip3_asset_fms_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_asset_fms_report/equip3_asset_fms_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_asset_fms_report.listing', {
#             'root': '/equip3_asset_fms_report/equip3_asset_fms_report',
#             'objects': http.request.env['equip3_asset_fms_report.equip3_asset_fms_report'].search([]),
#         })

#     @http.route('/equip3_asset_fms_report/equip3_asset_fms_report/objects/<model("equip3_asset_fms_report.equip3_asset_fms_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_asset_fms_report.object', {
#             'object': obj
#         })
