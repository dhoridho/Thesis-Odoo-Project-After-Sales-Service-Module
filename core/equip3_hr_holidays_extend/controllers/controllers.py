# -*- coding: utf-8 -*-
from datetime import timedelta
import datetime

import werkzeug
from dateutil.relativedelta import relativedelta

import odoo
from odoo import http, fields
from odoo.exceptions import UserError
from odoo.http import content_disposition, Controller, request, route
import json
from odoo.addons.survey.controllers.main import Survey
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment
from odoo.addons.survey.controllers.survey_session_manage import UserInputSession
import base64
import os
from odoo.exceptions import UserError, ValidationError


class LeaveController(http.Controller):
    @http.route(["/leave/<int:id>"], type='http', auth="public", website=True, csrf=False)
    def open_leave(self, id, **kw):
        action_id = request.env.ref('hr_holidays.hr_leave_action_action_approve_department')
        return request.redirect('/web?&#view_type=form&model=hr.leave&action=%s&id=%s' % (action_id.id,id))
    
    @http.route(["/cancelation/<int:id>"], type='http', auth="public", website=True, csrf=False)
    def open_cancelation(self, id, **kw):
        action_id = request.env.ref('equip3_hr_holidays_extend.hr_leave_cancel_action_department_url')
        return request.redirect('/web?&#view_type=form&model=hr.leave.cancelation&action=%s&id=%s' % (action_id.id,id))
    
    @http.route(["/allocation/<int:id>"], type='http', auth="public", website=True, csrf=False)
    def open_allocation(self, id, **kw):
        action_id = request.env.ref('hr_holidays.hr_leave_allocation_action_approve_department')
        return request.redirect('/web?&#view_type=form&model=hr.leave.allocation&action=%s&id=%s' % (action_id.id,id))
    
   
   




    