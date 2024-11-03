# -*- coding: utf-8 -*-
from odoo import api, models, fields, registry

class ResBranch(models.Model):
    _inherit = "res.branch"
 
    config_ids = fields.One2many(
        'pos.config',
        'pos_branch_id',
        string='POS of this Branch',
        readonly=1,
        help='Point of Sales has assigned of this Branch'
    )