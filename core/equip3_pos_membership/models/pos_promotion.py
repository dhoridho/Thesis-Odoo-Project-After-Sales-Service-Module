# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPromotion(models.Model):
    _inherit = 'pos.promotion'

    pos_loyalty_category = fields.Boolean('Promotion Groups')
    pos_loyalty_category_ids = fields.Many2many(
        'pos.loyalty.category',
        'pos_promotion_pos_loyalty_category_rel',
        'promotion_id',
        'loyalty_category_id',
        string='Member Groups')