# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class ShPurchaseTags(models.Model):
    _name = 'sh.purchase.tags'
    _description = 'Purchase Tags'

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index', default=1)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
