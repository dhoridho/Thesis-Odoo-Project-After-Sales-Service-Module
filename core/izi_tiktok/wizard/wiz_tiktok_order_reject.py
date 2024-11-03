# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class WizardTiktokOrderReject(models.TransientModel):
    _name = 'wiz.tiktok.order.reject'
    _description = 'Tiktok Order Reject Wizard'
    _rec_name = 'order_id'

    TTS_ORDER_STATUSES = [
        ('100', 'Unpaid'),
        ('111', 'Awaiting Shipment'),
        ('112', 'Awaiting Collection'),
        ('114', 'Partially Shipping'),
        ('121', 'In Transit'),
        ('122', 'Delivered'),
        ('130', 'Completed'),
        ('140', 'Cancelled'),
        ('201', 'Cancel Pending'),
        ('202', 'Cancel Reject'),
        ('203', 'Cancel Completed'),
    ]

    def _get_reason(self):
        if self._context.get('default_order_reason'):
            original_list = self._context.get('default_order_reason')
            tuple_list = [tuple(inner_list) for inner_list in original_list]
            return tuple_list
        else:
            return []

    mp_order_id = fields.Char(string='Order ID')
    order_id = fields.Many2one(comodel_name='sale.order', string='Order')
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='MP Account ID')
    order_status = fields.Selection(string="Status", selection=TTS_ORDER_STATUSES)
    order_reason = fields.Selection(selection=lambda self: self._get_reason(), string='Select a Reason')

    def confirm(self):
        if self.order_reason:
            response = self.mp_account_id.tiktok_request('post', '/api/reverse/order/cancel', {
                'order_id': self.mp_order_id,
                'cancel_reason_key': self.order_reason
            })
            if response.get('code') == 0:
                self.order_id.action_cancel()
                self.order_id.tiktok_fetch_order()
