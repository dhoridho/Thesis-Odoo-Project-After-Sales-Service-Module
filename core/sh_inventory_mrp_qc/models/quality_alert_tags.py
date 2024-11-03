# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api
import random


class ShQualityAlertTags(models.Model):
    _name = 'sh.qc.alert.tags'
    _description = 'Quality Alert Tags'
    _rec_name = 'name'

    name = fields.Char("Name", required=True)
    color = fields.Integer(string='Color Index')
    sequence = fields.Integer(string="Sequence")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]

    @api.model
    def create(self, vals):
        res = super(ShQualityAlertTags, self).create(vals)
        number = random.randrange(1, 10)
        res.color = number
        sequence = self.env['ir.sequence'].next_by_code('sh.qc.alert.tags')
        res.sequence = sequence
        return res
