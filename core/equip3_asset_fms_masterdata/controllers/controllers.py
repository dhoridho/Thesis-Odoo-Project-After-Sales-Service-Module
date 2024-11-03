# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3AssetFmsMasterdata(http.Controller):
#     @http.route('/equip3_asset_fms_masterdata/equip3_asset_fms_masterdata/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_asset_fms_masterdata/equip3_asset_fms_masterdata/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_asset_fms_masterdata.listing', {
#             'root': '/equip3_asset_fms_masterdata/equip3_asset_fms_masterdata',
#             'objects': http.request.env['equip3_asset_fms_masterdata.equip3_asset_fms_masterdata'].search([]),
#         })

#     @http.route('/equip3_asset_fms_masterdata/equip3_asset_fms_masterdata/objects/<model("equip3_asset_fms_masterdata.equip3_asset_fms_masterdata"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_asset_fms_masterdata.object', {
#             'object': obj
#         })
