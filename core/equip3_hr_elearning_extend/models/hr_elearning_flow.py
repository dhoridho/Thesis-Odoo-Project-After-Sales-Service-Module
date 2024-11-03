# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrElearningFlow(models.TransientModel):
    _name = 'hr.elearning.flow'

    name = fields.Char('Name', default='Hr E-Learning Flow')

    def action_none(self):
        return False