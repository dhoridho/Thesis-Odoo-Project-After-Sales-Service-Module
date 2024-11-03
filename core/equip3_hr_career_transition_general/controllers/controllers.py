# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrCareerTransitionGeneral(http.Controller):
#     @http.route('/equip3_hr_career_transition_general/equip3_hr_career_transition_general/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_career_transition_general/equip3_hr_career_transition_general/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_career_transition_general.listing', {
#             'root': '/equip3_hr_career_transition_general/equip3_hr_career_transition_general',
#             'objects': http.request.env['equip3_hr_career_transition_general.equip3_hr_career_transition_general'].search([]),
#         })

#     @http.route('/equip3_hr_career_transition_general/equip3_hr_career_transition_general/objects/<model("equip3_hr_career_transition_general.equip3_hr_career_transition_general"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_career_transition_general.object', {
#             'object': obj
#         })
