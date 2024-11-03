# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class TalentManagementFlow(models.TransientModel):
    _name = 'talent.management.flow'

    name = fields.Char('Name', default='Talent Management Flow')

    def action_none(self):
        return False