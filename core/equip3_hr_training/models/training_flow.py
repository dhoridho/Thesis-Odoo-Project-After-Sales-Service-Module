from odoo import api, fields, models


class HrTrainingFLow(models.Model):
    _name = 'hr.training.flow'
    _description = 'Training FLow'

    name = fields.Char(string='Name', default='HR Training Flow')

    def action_none(self):
        return False