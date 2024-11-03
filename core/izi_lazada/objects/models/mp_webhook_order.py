# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class MPWebhookOrder(models.Model):
    _inherit = 'mp.webhook.order'

    LZ_ORDER_STATUSES = [
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
        ('packed', 'Packed'),
        ('repacked', 'Repacked'),
        ('canceled', 'Canceled'),
        ('ready_to_ship', 'Ready To Ship'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('shipped', 'Shipped'),
        ('failed', 'Failed')
    ]

    lz_order_status = fields.Selection(string="Lazada Order Status", selection=LZ_ORDER_STATUSES, required=False)
    lz_order_id = fields.Char(string="Lazada Order ID", readonly=True, index=True)
    lz_order_line_id = fields.Char(string="Lazada Order Line ID", readonly=True, index=True)
    lz_reverse_order_id = fields.Char(string="Lazada Reverse Order Line ID", readonly=True)
    lz_reverse_order_line_id = fields.Char(string="Lazada Reverse Order Line ID", readonly=True)

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, lz_order_status_field = 'lazada', 'lz_order_status'
        lz_order_statuses = {
            'waiting': ['unpaid'],
            'to_cancel': [],
            'cancel': ['canceled'],
            'to_process': ['pending', 'repacked'],
            'in_process': ['packed'],
            'to_ship': ['ready_to_ship'],
            'in_ship': ['shipped'],
            'delivered': [],
            'done': ['delivered'],
            'return': []
        }
        mp_order_statuses.append((marketplace, (lz_order_status_field, lz_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.LZ_ORDER_STATUSES)))
        super(MPWebhookOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    # @api.multi
    @api.depends('lz_order_status')
    def _compute_mp_order_status(self):
        super(MPWebhookOrder, self)._compute_mp_order_status()

    def lazada_fetch_webhook_order(self):
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
