# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah


from odoo import http
from odoo.http import *
import hmac
import logging
import json
import time

from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder

_logger = logging.getLogger(__name__)


class IZILazadaWebhook(http.Controller):
    @http.route('/api/izi/webhook/lz/order', methods=['POST', 'GET'], type='json', auth='public')
    def sp_order(self, **kw):
        # _logger.info('SHOPEE_WEBHOOK_DATA > Start')
        if request._request_type == 'json':
            json_body = request.jsonrequest

            '''
            {
                "seller_id": "1234567",  # seller id
                "message_type": 0,
                "data": {
                    "order_status": "unpaid",  # Order status
                    "status_update_time": 1603698638,  # timestamp of the order status update
                    "trade_order_id": "260422900198363",  # trade order id which mapping to the order_id in API
                    "trade_order_line_id": "260422900298363"  # sub order id.
                },
                "timestamp": 1603766859530,  # timestamp of push
                "site": "lazada_vn"  # site info
            }
            '''
            mp_account = request.env['mp.account'].sudo().search(
                [('lz_seller_id.seller_id', '=', str(json_body.get('seller_id')))])
            mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
            if mp_account:
                if json_body.get('message_type') == 0:
                    # _logger.info('SHOPEE_WEBHOOK_ORDER > Notification Shopee Order: %s with status %s' %
                    #              (json_body.get('data').get('ordersn'), json_body.get('data').get('status')))
                    mp_invoice_number = json_body.get('data').get('trade_order_id')
                    lz_order_line_id = json_body.get('data').get('trade_order_line_id')

                    # Create or Write Webhook Order
                    mp_existing_order = mp_webhook_order_obj.search(
                        [('mp_invoice_number', '=', mp_invoice_number),
                         ('lz_order_line_id', '=', lz_order_line_id),
                         ('mp_account_id', '=', mp_account.id)], limit=1)

                    update_order_time = datetime.fromtimestamp(time.mktime(
                        time.gmtime(json_body.get('data').get('status_update_time'))))
                    vals = {
                        'mp_invoice_number': mp_invoice_number,
                        'lz_order_id': mp_invoice_number,
                        'lz_order_line_id': json_body.get('data').get('trade_order_line_id'),
                        'lz_reverse_order_id': json_body.get('data').get('reverse_order_id', None),
                        'lz_reverse_order_line_id': json_body.get('data').get('reverse_order_line_id', None),
                        'mp_account_id': mp_account.id,
                        'order_update_time': update_order_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'lz_order_status': json_body.get('data').get('order_status'),
                        'raw': json.dumps(json_body, indent=4),
                        'is_process': False
                    }

                    # if json_body.get('data').get('shipping_document_info', False):
                    #     vals.update({
                    #         'mp_awb_number': json_body.get('data').get('shipping_document_info').get('tracking_number')
                    #     })
                    # if json_body.get('data').get('create_time', False):
                    #     vals.update({
                    #         'order_create_time': datetime.fromtimestamp(
                    #             time.mktime(time.gmtime(json_body.get('data').get('create_time'))))
                    #         .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    #     })

                    if mp_existing_order:
                        if mp_existing_order.order_update_time <= update_order_time:
                            order_status_old = mp_existing_order.lz_order_status
                            mp_existing_order.write(vals)
                            _logger.info('LAZADA_WEBHOOK_ORDER > Success Update Lazada Order: %s from status %s to %s' %
                                         (json_body.get('data').get('ordersn'), order_status_old, mp_existing_order.lz_order_status))
                    else:
                        mp_webhook_order_obj.create(vals)
                        _logger.info('LAZADA_WEBHOOK_ORDER > Success Create Lazada Order: %s with status %s' %
                                     (json_body.get('data').get('ordersn'), json_body.get('data').get('order_status')))

        res = Response('Success', status=200)
        return res
