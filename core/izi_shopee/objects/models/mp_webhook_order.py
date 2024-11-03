# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPWebhookOrder(models.Model):
    _inherit = 'mp.webhook.order'

    SP_ORDER_STATUSES = [
        ('UNPAID', 'Unpaid'),
        ('READY_TO_SHIP', 'Ready to Ship'),
        ('PROCESSED', 'Processed'),
        ('SHIPPED', 'Shipped'),
        ('COMPLETED', 'Completed'),
        ('TO_CONFIRM_RECEIVE', 'In Confirm Receive'),
        ('IN_CANCEL', 'In Cancel'),
        ('CANCELLED', 'Cancelled'),
        ('TO_RETURN', 'To Return'),
    ]

    sp_order_status = fields.Selection(string="Shopee Order Status", selection=SP_ORDER_STATUSES, required=False)
    sp_order_id = fields.Char(string="Shopee Order ID", readonly=True)
    sp_package_number = fields.Char(string="Shopee Package Number", readonly=True)
    sp_forder_id = fields.Char(string="Shopee Forder ID", readonly=True)

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, sp_order_status_field = 'shopee', 'sp_order_status'
        sp_order_statuses = {
            'waiting': ['UNPAID'],
            'to_cancel': ['IN_CANCEL'],
            'cancel': ['CANCELLED'],
            'to_process': [],
            'in_process': ['READY_TO_SHIP'],
            'to_ship': ['PROCESSED'],
            'in_ship': ['SHIPPED'],
            'done': ['TO_CONFIRM_RECEIVE', 'COMPLETED'],
            'return': ['TO_RETURN']
        }
        mp_order_statuses.append((marketplace, (sp_order_status_field, sp_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.SP_ORDER_STATUSES)))
        super(MPWebhookOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    # @api.multi
    @api.depends('sp_order_status')
    def _compute_mp_order_status(self):
        super(MPWebhookOrder, self)._compute_mp_order_status()

    def shopee_fetch_webhook_order(self):
        wiz_mp_webhook_order_obj = self.env['wiz.mp.webhook.order']
        mp_invoice_number_list = []
        for rec in self:
            mp_invoice_number_list.append(rec.mp_invoice_number)
        wiz_mp_webhook_order = wiz_mp_webhook_order_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_invoice_number',
            'mp_invoice_number': ','.join(mp_invoice_number_list)
        })
        return wiz_mp_webhook_order.get_webhook_order()
