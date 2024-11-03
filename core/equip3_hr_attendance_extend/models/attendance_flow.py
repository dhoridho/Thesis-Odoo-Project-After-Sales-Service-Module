# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AttendanceFlow(models.TransientModel):
    _name = 'attendance.flow'

    name = fields.Char('Name', default='Attendance Flow')

    def action_none(self):
        pass