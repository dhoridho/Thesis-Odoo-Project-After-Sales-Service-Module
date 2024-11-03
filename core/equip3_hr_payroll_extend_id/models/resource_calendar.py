# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResourseCalendar(models.Model):
    _inherit = 'resource.calendar'

    late_dedution_rules_id = fields.Many2one('late.deduction.rule', domain=[('active', '=', True)])
