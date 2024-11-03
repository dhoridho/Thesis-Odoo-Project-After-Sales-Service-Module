# -*- coding: utf-8 -*-
# from odoo import http


# class Equip3RentalAvailability(http.Controller):
#     @http.route('/equip3_rental_availability/equip3_rental_availability/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/equip3_rental_availability/equip3_rental_availability/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('equip3_rental_availability.listing', {
#             'root': '/equip3_rental_availability/equip3_rental_availability',
#             'objects': http.request.env['equip3_rental_availability.equip3_rental_availability'].search([]),
#         })

#     @http.route('/equip3_rental_availability/equip3_rental_availability/objects/<model("equip3_rental_availability.equip3_rental_availability"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('equip3_rental_availability.object', {
#             'object': obj
#         })
