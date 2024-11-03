# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrLeaveFlow(models.TransientModel):
    _name = 'hr.leave.flow'

    name = fields.Char('Name', default='HR Leave Flow')

    def action_none(self):
        return False