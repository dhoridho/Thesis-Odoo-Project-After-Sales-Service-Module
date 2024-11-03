from odoo import api, fields, models, _


class CouponCoupon(models.Model):
    _inherit = 'coupon.coupon'

    hotel_reservation_order_id = fields.Many2one(
        'hotel.reservation', string='Reservation Order')
    reservation_order_id = fields.Many2one(
        'hotel.reservation', string='Reservation Order')
