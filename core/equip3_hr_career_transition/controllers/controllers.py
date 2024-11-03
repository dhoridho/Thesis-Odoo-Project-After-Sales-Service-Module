# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3HrCareerTransition(http.Controller):
#     @http.route('/equip3_hr_career_transition/equip3_hr_career_transition/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_hr_career_transition/equip3_hr_career_transition/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_hr_career_transition.listing', {
#             'root': '/equip3_hr_career_transition/equip3_hr_career_transition',
#             'objects': http.request.env['equip3_hr_career_transition.equip3_hr_career_transition'].search([]),
#         })

#     @http.route('/equip3_hr_career_transition/equip3_hr_career_transition/objects/<model("equip3_hr_career_transition.equip3_hr_career_transition"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_hr_career_transition.object', {
#             'object': obj
#         })
