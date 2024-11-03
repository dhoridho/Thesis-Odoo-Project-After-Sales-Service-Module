from odoo import api, fields, models


class HrTravelFlow(models.Model):
    _name = 'hr.travel.flow'
    _description = 'HR Travel Flow'

    name = fields.Char(string='Name', default='HR Travel Flow')

    def action_none(self):
        return False