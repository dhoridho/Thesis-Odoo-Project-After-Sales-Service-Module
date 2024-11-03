from odoo import api, fields, models


class HrCareerTransitionFlow(models.Model):
    _name = 'career.transition.flow'
    _description = 'Career Transition FLow'

    name = fields.Char(string='Name', default='Career Transition Flow')

    def action_none(self):
        return False
