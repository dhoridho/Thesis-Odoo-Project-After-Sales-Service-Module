# -*- coding: utf-8 -*

from datetime import datetime
from odoo import fields, models

class PosCoupon(models.Model):
    _inherit = 'pos.coupon'

    def disable_expired_coupon_cron(self):
        domain = [('active','=',True), ('state','=','active'), ('end_date','<', datetime.now())]
        coupons = self.env['pos.coupon'].search(domain)
        coupons.write({ 'active': False, 'state': 'expired' })