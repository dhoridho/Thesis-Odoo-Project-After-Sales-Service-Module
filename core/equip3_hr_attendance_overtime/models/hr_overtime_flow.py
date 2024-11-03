from odoo import api, fields, models, _


class OvertimeFlow(models.TransientModel):
    _name = 'hr.overtime.flow'

    name = fields.Char('Name', default='Employee Flow')

    def action_none(self):
        pass
