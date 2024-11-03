# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosCouponApplyCode(models.TransientModel):
    _name = 'pos.coupon.apply.code'
    _rec_name = 'coupon_code'
    _description = 'POS Coupon Apply Code'

    coupon_code = fields.Char(string="Code", required=True)



