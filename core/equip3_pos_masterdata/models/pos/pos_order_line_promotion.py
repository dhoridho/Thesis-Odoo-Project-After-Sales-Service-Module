# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosPromotion(models.Model):
    _name = 'pos.order.line.promotion'
    _description = 'POS Order Line Promotion for Promotion Stack'
    _order = 'sequence'
    _rec_name = 'promotion_id'

    sequence = fields.Integer('Sequence', default=0)
    pos_order_line_id = fields.Many2one('pos.order.line', 'POS Order Line')
    promotion_id = fields.Many2one('pos.promotion', 'Promotion')
    promotion_disc = fields.Float('Promotion (Discount %)', digits=(16, 4))
    
    price = fields.Float('Price (After Discount)')
    amount_percentage = fields.Float('Discount Amount (Percentage %)', digits=(16, 4))
    amount = fields.Float('Discount Amount')