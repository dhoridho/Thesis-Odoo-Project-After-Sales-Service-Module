# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website.controllers.main import Website

# class MyModule(http.Controller):
#     @http.route('/my_module/my_module/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/my_module/my_module/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('my_module.listing', {
#             'root': '/my_module/my_module',
#             'objects': http.request.env['my_module.my_module'].search([]),
#         })

#     @http.route('/my_module/my_module/objects/<model("my_module.my_module"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('my_module.object', {
#             'object': obj
#         })


class BackendControllerInherit(Website):
    """Website Inherit"""

    @http.route('/switch/user/company', type='json', auth="user")
    def switch_user_company_details(self, company_id, **kw):
        """Check selected user company"""
        consignment_menu = request.env.ref('equip3_consignment_sales.sale_consign_menu')
        consignment_report_menu = request.env.ref('equip3_consignment_sales.consignment_report_header')
        
        company = request.env['res.company'].browse(company_id)
        if company and company.is_consignment_sales:
            consignment_menu.sudo().update({'active': True})
            consignment_report_menu.sudo().update({'active': True})
        else:
            consignment_menu.sudo().update({'active': False})
            consignment_report_menu.sudo().update({'active': False})
