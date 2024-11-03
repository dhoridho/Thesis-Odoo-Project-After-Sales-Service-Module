# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
import json

_logger = logging.getLogger(__name__)


class RoomDashboardController(http.Controller):

    @http.route('/hotel_room_dashboard/web', type='http', auth='user')
    def a(self, debug=False, **k):
        # print ("request.session.uid-----------",request.session.uid)
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=/hotel_room_dashboard/web')
        context = {
            'session_info': json.dumps(request.env['ir.http'].session_info())
        }
        return request.render('hotel_room_dashboard_view.room_dashboard', qcontext=context)
