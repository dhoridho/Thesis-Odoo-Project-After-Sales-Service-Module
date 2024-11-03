# -*- coding: utf-8 -*
from odoo import api, fields, models, _

class HourGroup(models.Model):
    _name = 'hour.group'
    _description = 'Hour Group'

    name = fields.Char()
    start_hour = fields.Float()
    end_hour = fields.Float()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
