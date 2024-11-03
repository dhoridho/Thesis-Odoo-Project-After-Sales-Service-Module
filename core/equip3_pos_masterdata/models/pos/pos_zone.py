# -*- coding: utf-8 -*-

from odoo import api, models, fields

class PosZone(models.Model):
    _name = 'pos.zone'
    _description = 'Pos Zone'

    name = fields.Char('Name', required=1)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
