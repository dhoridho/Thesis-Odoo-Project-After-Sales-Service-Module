# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    booking_count = fields.Integer("Bookings", compute='_compute_booking_count')

    def _compute_booking_count(self):
        for partner in self:
            operator = 'child_of' if partner.is_company else '='  # the opportunity count should counts the opportunities of this company and all its contacts
            # partner.booking_count = self.env['booking.booking'].search_count(
            #     [('partner_id', operator, partner.id)])
            partner.booking_count = len(self.env['booking.booking'].search(
                [('partner_id', '=', self.id),('state','=','confirm')]))


    def send_whatsapp_msg(self):
        if self.mobile:
            mobile_num = self.mobile.replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(
                ")", "")
            return {
                'type': 'ir.actions.act_url',
                'url': "https://api.whatsapp.com/send?phone=" + mobile_num,
                'target': '_blank',
                'res_id': self.id,
            }
