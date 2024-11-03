# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time
import json
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder

TIME_MODE_ORDER = [
    ('create_time', 'Base on Order Create Time'),
    ('update_time', 'Base on Order Update Time')
]


class WizardShopeeWebhookOrder(models.TransientModel):
    _name = 'wiz.sp_webhook_order'
    _description = 'Shopee Webhook Order Wizard'

    mp_account_id = fields.Many2one('mp.account', 'Account')
    range_type = fields.Selection(string="Time Mode", selection=TIME_MODE_ORDER)
    start_time = fields.Datetime('Start Time')
    end_time = fields.Datetime('End Time')

    @mp.shopee.capture_error
    def confirm(self):
        mp_webhook_order_obj = self.env['mp.webhook.order'].sudo()
        mp_account = self.mp_account_id
        mp_account_ctx = mp_account.generate_context()
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        account_params = {}
        order_params = {}
        if mp_account.mp_token_id.state == 'valid':
            account_params = {'access_token': mp_account.mp_token_id.name}
        sp_account = mp_account.shopee_get_account(**account_params)
        sp_order_v2 = ShopeeOrder(sp_account, sanitizers=order_obj.get_sanitizers(mp_account.marketplace))

        from_time = self.start_time
        to_time = self.end_time
        order_params.update({
            'from_date': from_time,
            'to_date': to_time,
            'limit': mp_account_ctx.get('order_limit'),
            'time_mode': self.range_type,
        })
        sp_order_list = sp_order_v2.get_order_list(**order_params)
        sp_data_raws = sp_order_v2.get_order_detail(sp_data=sp_order_list)
        sp_orders_by_mpexid = {}
        sp_orders = mp_webhook_order_obj.search([('mp_account_id', '=', mp_account.id)])
        for order in sp_orders:
            sp_orders_by_mpexid[order.mp_invoice_number] = order

        index = 0
        for sp_order in sp_data_raws:
            index = index + 1
            # _logger(mp_account.marketplace, 'Processing order %s from %s of total orders imported!' % (
            #     str(index), len(sp_data_raws)
            # ), notify=True, notif_sticky=False)
            mp_invoice_number = sp_order.get('order_sn')
            # Create or Write Webhook Order
            mp_existing_order = sp_orders_by_mpexid[mp_invoice_number] if mp_invoice_number in sp_orders_by_mpexid else False
            rec_values = {
                'mp_invoice_number': mp_invoice_number,
                'sp_order_id': sp_order.get('order_sn'),
                'mp_account_id': mp_account.id,
                'order_update_time': datetime.fromtimestamp(
                    time.mktime(time.gmtime(sp_order.get('update_time'))))
                .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'order_create_time': datetime.fromtimestamp(
                    time.mktime(time.gmtime(sp_order.get('create_time'))))
                .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'sp_order_status': sp_order.get('order_status'),
                'raw': json.dumps(sp_order, indent=4),
            }
            if mp_existing_order:
                # _logger(mp_account.marketplace, 'Updating Order %s ' %
                #         (mp_invoice_number), notify=True, notif_sticky=False)
                mp_existing_order.write(rec_values)
            else:
                # _logger(mp_account.marketplace, 'Creating Order %s ' %
                #         (mp_invoice_number), notify=True, notif_sticky=False)
                mp_webhook_order_obj.create(rec_values)
