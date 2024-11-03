# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayrollFlow(models.TransientModel):
    _name = 'hr.payroll.flow'

    name = fields.Char('Name', default='Hr Payroll Flow')

    def action_none(self):
        return False