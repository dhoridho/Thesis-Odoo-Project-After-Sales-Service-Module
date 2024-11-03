# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time
import json
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


from odoo.addons.izi_marketplace.objects.utils.tools import mp
# from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder

TIME_MODE_ORDER = [
    ('create_time', 'Base on Order Create Time'),
    ('update_time', 'Base on Order Update Time')
]

PARAMS = [
    ('by_date_range', 'By Date Range'),
    ('by_mp_invoice_number', 'By MP Invoice Number'),
]


class WizardMPWebhookOrder(models.TransientModel):
    _name = 'wiz.mp.webhook.order'
    _description = 'MP Webhook Order Wizard'

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="MP Account", required=True)
    marketplace = fields.Selection(related="mp_account_id.marketplace", string="Marketplace")
    range_type = fields.Selection(string="Time Mode", selection=TIME_MODE_ORDER, default='create_time')
    from_date = fields.Datetime('Start Time')
    to_date = fields.Datetime('End Time')
    mp_invoice_number = fields.Char(string="MP Invoice Number", required=False)
    params = fields.Selection(string="Parameter", selection=PARAMS, required=True, default="by_date_range")

    def get_webhook_order(self):
        kwargs = {'params': self.params,
                  'force_update': self._context.get('force_update', False),
                  'time_mode': self.range_type}
        if self.params == 'by_date_range':
            from_date = fields.Datetime.from_string(self.from_date)
            to_date = fields.Datetime.from_string(self.to_date)
            if from_date > to_date:
                raise ValidationError(
                    "Invalid date range, from_date higher than to_date. Please input correct date range!")
            kwargs.update({'from_date': from_date, 'to_date': to_date})
        elif self.params == 'by_mp_invoice_number':
            kwargs.update({'mp_invoice_number': self.mp_invoice_number})
        if hasattr(self.mp_account_id, '%s_get_webhook_orders' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_webhook_orders' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
