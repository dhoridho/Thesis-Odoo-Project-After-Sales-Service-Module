# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrRecruitmentFlow(models.TransientModel):
    _name = 'hr.recruitment.flow'

    name = fields.Char('Name', default='Hr Recruitment Flow')

    def action_none(self):
        return False