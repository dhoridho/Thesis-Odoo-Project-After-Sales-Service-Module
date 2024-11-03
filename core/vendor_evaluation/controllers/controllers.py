# -*- coding: utf-8 -*-
from odoo import http

# class HelloWorld(http.Controller):
#     @http.route('/hello_world/hello_world/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hello_world/hello_world/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hello_world.listing', {
#             'root': '/hello_world/hello_world',
#             'objects': http.request.env['hello_world.hello_world'].search([]),
#         })

#     @http.route('/hello_world/hello_world/objects/<model("hello_world.hello_world"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hello_world.object', {
#             'object': obj
#         })