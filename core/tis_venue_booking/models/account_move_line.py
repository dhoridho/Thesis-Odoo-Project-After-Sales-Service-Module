# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import fields, api, models, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    _description = 'Account Move Line'

    booking_line_ids = fields.Many2many(
        'booking.amenities',
        'booking_order_line_invoice_rel', 'invoice_line_id', 'amenities_line_id',
        string='Booking Order Lines', readonly=True, copy=False)

    def _copy_data_extend_business_fields(self, values):
        super(AccountMoveLine, self)._copy_data_extend_business_fields(values)
        values['booking_line_ids'] = [(6, None, self.booking_line_ids.ids)]
