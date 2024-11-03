
from odoo import api , fields , models, _


class CouponReward(models.Model):
    _inherit = 'coupon.reward'

    reward_product_id = fields.Many2one(domain=['|', ('sale_ok', '=', True), ('purchase_ok', '=', True)])
