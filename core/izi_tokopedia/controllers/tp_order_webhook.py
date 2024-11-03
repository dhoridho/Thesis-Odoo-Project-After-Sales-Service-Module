# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import http
# from odoo.http import *
from odoo.http import request, Response
import logging
import json
import pytz
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class IZITokopediaWebhook(http.Controller):
    def from_api_timestamp(self, api_ts, as_tz='UTC'):
        api_tz = pytz.timezone('Asia/Jakarta')
        as_tz = pytz.timezone(as_tz)
        api_dt = datetime.fromtimestamp(api_ts)
        return api_tz.localize(api_dt).astimezone(as_tz)

    @http.route('/api/izi/webhook/tp/order/notification', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_notification(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            fs_id = json_body.get('fs_id', False)
            mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
            # _logger.info('New Order From Tokopedia: %s' % (json_body.get('order_id,', '')))
            if fs_id:
                mp_account = request.env['mp.account'].sudo().search([('tp_fs_id', '=', fs_id)])
                if mp_account.mp_webhook_state == 'registered':
                    mp_existing_order = mp_webhook_order_obj.search(
                        [('tp_order_id', '=', json_body.get('order_id')),
                         ('mp_account_id', '=', mp_account.id)], limit=1)
                    create_order_time = self.from_api_timestamp(json_body.get('create_time'))
                    order_status = str(json_body.get('order_status'))
                    vals = {
                        'mp_invoice_number': json_body.get('invoice_ref_num', ''),
                        'tp_order_id': str(json_body.get('order_id', False)),
                        'mp_account_id': mp_account.id,
                        'order_create_time': create_order_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'tp_order_status': order_status,
                        'raw': json.dumps(json_body, indent=4),
                        'is_process': False
                    }
                    if mp_existing_order:
                        if mp_existing_order.order_create_time <= create_order_time:
                            order_status_old = mp_existing_order.tp_order_status
                            mp_existing_order.write(vals)
                            # _logger.info('WEBHOOK_ORDER > Success Update Tokopedia Order: %s from status %s to %s' %
                            #              (vals['tp_order_id'], order_status_old, mp_existing_order.tp_order_status))
                    else:
                        mp_webhook_order_obj.create(vals)
                        # _logger.info('WEBHOOK_ORDER > Success Create Tokopedia Order: %s with status %s' %
                        #              (vals['mp_invoice_number'], vals['tp_order_status']))
                    # _logger.info('Success Create Tokopedia Order: %s with status %s' %
                    #              (vals['mp_invoice_number'], order_status))
                    # kwargs = {'params': 'by_mp_invoice_number',
                    #           'mp_order_id': json_body.get('order_id'),
                    #           'force_update': mp_account._context.get('force_update', False)}
                    # if hasattr(mp_account, '%s_get_orders' % marketplace):
                    #     getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res

    @http.route('/api/izi/webhook/tp/order/request/cancel', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_cancel(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
            mp_account = request.env['mp.account'].sudo().search([('marketplace', '=', 'tokopedia')], limit=1)
            mp_existing_order = mp_webhook_order_obj.search(
                [('tp_order_id', '=', json_body.get('order_id')),
                 ('mp_account_id', '=', mp_account.id)], limit=1)
            if mp_existing_order:
                vals = {
                    'tp_order_status': '401',
                    'is_process': False
                }
                order_status_old = mp_existing_order.tp_order_status
                mp_existing_order.write(vals)
                # _logger.info('WEBHOOK_ORDER > Success Update Tokopedia Order: %s from status %s to %s' %
                #              (mp_existing_order.mp_invoice_number, order_status_old, mp_existing_order.tp_order_status))
            # if mp_account.mp_webhook_state == 'registered':
            #     marketplace = mp_account.marketplace
            #     kwargs = {'params': 'by_mp_invoice_number',
            #               'mp_order_id': json_body.get('order_id'),
            #               'force_update': mp_account._context.get('force_update', False)}
            #     if hasattr(mp_account, '%s_get_orders' % marketplace):
            #         getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res

    @http.route('/api/izi/webhook/tp/order/status', methods=['POST', 'GET'], type='json', auth='public')
    def tp_order_status(self, **kw):
        if request._request_type == 'json':
            json_body = request.jsonrequest
            # _logger.info('TOKOPEDIA_WEBHOOK_DATA > Read JSON, %s' % (json_body))
            fs_id = json_body.get('fs_id', False)
            order_status = str(json_body.get('order_status'))
            mp_webhook_order_obj = request.env['mp.webhook.order'].sudo()
            if order_status not in ['220', '221', '11', '100', '103', '200']:
                if fs_id:
                    # _logger.info('New Order Status Change From Tokopedia: %s with status %s' %
                    #              (json_body.get('order_id,', ''), json_body.get('order_status')))
                    mp_account = request.env['mp.account'].sudo().search([('tp_fs_id', '=', fs_id)])
                    mp_existing_order = mp_webhook_order_obj.search(
                        [('tp_order_id', '=', json_body.get('order_id')),
                         ('mp_account_id', '=', mp_account.id)], limit=1)
                    # create_order_time = self.from_api_timestamp(json_body.get('create_time'))
                    vals = {
                        'mp_invoice_number': json_body.get('invoice_ref_num', ''),
                        'tp_order_id': str(json_body.get('order_id', False)),
                        'mp_account_id': mp_account.id,
                        # 'order_create_time': create_order_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'tp_order_status': order_status,
                        'raw': json.dumps(json_body, indent=4),
                        'is_process': False
                    }
                    if mp_existing_order:
                        # if mp_existing_order.order_create_time <= create_order_time:
                        order_status_old = mp_existing_order.tp_order_status
                        mp_existing_order.write(vals)
                        # _logger.info('TOKOPEDIA_WEBHOOK_ORDER > Success Update Tokopedia Order: %s from status %s to %s' %
                        #              (vals['mp_invoice_number'], order_status_old, mp_existing_order.tp_order_status))
                    else:
                        mp_webhook_order_obj.create(vals)
                        # _logger.info('TOKOPEDIA_WEBHOOK_ORDER > Success Create Tokopedia Order: %s with status %s' %
                        #              (vals['mp_invoice_number'], vals['tp_order_status']))

                    # if mp_account.mp_webhook_state == 'registered':
                    #     marketplace = mp_account.marketplace
                    #     kwargs = {'params': 'by_mp_invoice_number',
                    #               'mp_order_id': json_body.get('order_id'),
                    #               'force_update': mp_account._context.get('force_update', False),
                    #               'skip_create': True}
                    #     if hasattr(mp_account, '%s_get_orders' % marketplace):
                    #         getattr(mp_account, '%s_get_orders' % marketplace)(**kwargs)
        res = Response('Success', status=200)
        return res
