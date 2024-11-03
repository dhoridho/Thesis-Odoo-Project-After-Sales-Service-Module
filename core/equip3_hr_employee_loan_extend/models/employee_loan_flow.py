# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class EmployeeLoanFlow(models.TransientModel):
    _name = 'employee.loan.flow'

    name = fields.Char('Name', default='Employee Loan Flow')

    def action_none(self):
        return False