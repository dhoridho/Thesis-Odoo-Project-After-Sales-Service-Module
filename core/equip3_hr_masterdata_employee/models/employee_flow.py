from odoo import api, fields, models, _


class EmployeeFlow(models.TransientModel):
    _name = 'employee.flow'

    name = fields.Char('Name', default='Employee Flow')

    def action_button_none(self):
        pass
