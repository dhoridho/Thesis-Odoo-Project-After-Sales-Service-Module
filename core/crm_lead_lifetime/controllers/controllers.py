# -*- coding: utf-8 -*-
from odoo import http

# class CrmLeadAge(http.Controller):
#     @http.route('/crm_lead_age/crm_lead_age/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_lead_age/crm_lead_age/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_lead_age.listing', {
#             'root': '/crm_lead_age/crm_lead_age',
#             'objects': http.request.env['crm_lead_age.crm_lead_age'].search([]),
#         })

#     @http.route('/crm_lead_age/crm_lead_age/objects/<model("crm_lead_age.crm_lead_age"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_lead_age.object', {
#             'object': obj
#         })