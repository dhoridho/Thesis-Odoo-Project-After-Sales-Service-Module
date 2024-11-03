# -*- coding: utf-8 -*-


from odoo import http
from odoo.http import request

from odoo.addons.calendar.controllers.main import CalendarController


class JointCalendarController(CalendarController):
    """
    Re-write to add check by joint calendar notifications
    """

    @http.route('/calendar/jointnotify', type='json', auth="user")
    def notify_joint(self):
        """
        Joint events notifications route
        """
        return request.env['calendar.alarm_manager'].get_next_notif_joint()
