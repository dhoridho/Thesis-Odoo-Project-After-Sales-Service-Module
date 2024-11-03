from odoo import api, fields, models, _


class TimesheetFlow(models.TransientModel):
    _name = 'hr.timesheet.flow'

    name = fields.Char('Name', default='Expense Flow')

    def action_none(self):
        pass
