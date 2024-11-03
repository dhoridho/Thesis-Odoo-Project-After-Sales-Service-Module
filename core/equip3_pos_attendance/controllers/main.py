# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Session


class Equip2Session(Session):

    @http.route()
    def logout(self, redirect='/web'):
        user = request.env['res.users'].sudo().search([('id','=',request.session['uid'])]) 
        if user:
        	user.action_pos_attendance_checked_out() 
        	
        response = super(Equip2Session, self).logout(redirect) 
        return response