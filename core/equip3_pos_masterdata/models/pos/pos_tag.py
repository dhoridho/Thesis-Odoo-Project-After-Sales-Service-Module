# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PosTag(models.Model):
    _name = "pos.tag"
    _description = "Management Order line tags"

    name = fields.Char('Name', required=1)
    color = fields.Char("Color Tag", default=0)
    is_return_reason = fields.Boolean('Is return Reason')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)