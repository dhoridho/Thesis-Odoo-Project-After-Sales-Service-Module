# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosFlow(models.TransientModel):
    _name = 'pos.flow'
    _description = 'Pos Flow'

    name = fields.Char('Name', default='Point of Sale Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result