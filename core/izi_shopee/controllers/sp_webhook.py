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


class IZIShopeeWebhook(http.Controller):

    # def verify_push_msg(self, url, request_body, partner_key, authorization):
    #     base_string = url + '|' + request_body
    #     call_auth = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()
    #     if call_auth != authorization:
    #         return False
    #     else:
    #         return True

    @http.route('/api/izi/webhook/sp/order', methods=['POST', 'GET'], type='json', auth='public')
    def sp_order(self, **kw):
        # _logger.info('SHOPEE_WEBHOOK_DATA > Start')
        if request._request_type == 'json':
            json_body = request.jsonrequest
            # _logger.info('SHOPEE_WEBHOOK_DATA > WEBHOOK_CODE_%s' % (json_body.get('code')))
            # _logger.info('SHOPEE_WEBHOOK_DATA > Read JSON, %s' % (json_body))
            # authorization = request.httprequest.headers.environ.get('HTTP_AUTHORIZATION')
            # url = request.httprequest.url
            # http_body = request.httprequest.data.decode()
            shopee_shop = request.env['mp.shopee.shop'].sudo().search(
                [('shop_id', '=', str(json_body.get('shop_id')))])
            mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
            if shopee_shop:
                mp_account = shopee_shop.mp_account_id
                # mp_account_ctx = mp_account.generate_context()
                # order_obj = request.env['sale.order'].sudo().with_context(mp_account_ctx)
                # _logger.info('SHOPEE_WEBHOOK_DATA > Shop ID : %s' % (str(json_body.get('shop_id'))))
                # verify_push_msg = self.verify_push_msg(url, http_body, mp_account.sp_partner_key, authorization)
                if json_body.get('code') == 3:
                    # _logger.info('SHOPEE_WEBHOOK_ORDER > Notification Shopee Order: %s with status %s' %
                    #              (json_body.get('data').get('ordersn'), json_body.get('data').get('status')))
                    mp_invoice_number = json_body.get('data').get('ordersn')

                    # if mp_account.mp_token_id.state == 'valid':
                    #     account_params = {'access_token': mp_account.mp_token_id.name}
                    #     sp_account = mp_account.shopee_get_account(**account_params)
                    #     sp_order_v2 = ShopeeOrder(
                    #         sp_account, sanitizers=order_obj.get_sanitizers(mp_account.marketplace))
                    #     sp_data_raws = sp_order_v2.get_order_detail(**{
                    #         'order_ids': [mp_invoice_number]
                    #     })
                    #     json_body.update({
                    #         'data': sp_data_raws[0]
                    #     })

                    # Create or Write Webhook Order
                    mp_existing_order = mp_webhook_order_obj.search(
                        [('mp_invoice_number', '=', mp_invoice_number)], limit=1)
                    update_order_time = datetime.fromtimestamp(time.mktime(
                        time.gmtime(json_body.get('data').get('update_time'))))
                    vals = {
                        'mp_invoice_number': mp_invoice_number,
                        'sp_order_id': mp_invoice_number,
                        'mp_account_id': mp_account.id,
                        'order_update_time': update_order_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'sp_order_status': json_body.get('data').get('status') or json_body.get('data').get('order_status'),
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
                            order_status_old = mp_existing_order.sp_order_status
                            mp_existing_order.write(vals)
                            # _logger.info('SHOPEE_WEBHOOK_ORDER > Success Update Shopee Order: %s from status %s to %s' %
                            #              (json_body.get('data').get('ordersn'), order_status_old, mp_existing_order.sp_order_status))
                    else:
                        mp_webhook_order_obj.create(vals)
                        # _logger.info('SHOPEE_WEBHOOK_ORDER > Success Create Shopee Order: %s with status %s' %
                        #              (json_body.get('data').get('ordersn'), json_body.get('data').get('status') or json_body.get('data').get('order_status')))

                elif json_body.get('code') == 4:
                    mp_invoice_number = json_body.get('data').get('ordersn')
                    mp_existing_order = mp_webhook_order_obj.search(
                        [('mp_invoice_number', '=', mp_invoice_number)], limit=1)
                    if mp_existing_order:
                        mp_existing_order.write({
                            'sp_order_status': 'PROCESSED',
                            'mp_awb_number': json_body.get('data').get('tracking_no'),
                            'sp_package_number': json_body.get('data').get('package_number'),
                            'sp_forder_id': json_body.get('data').get('forder_id'),
                            'is_process': False
                        })

        res = Response('Success', status=200)
        return res
