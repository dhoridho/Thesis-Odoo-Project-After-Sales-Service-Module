# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
from email.policy import default
from dateutil.relativedelta import relativedelta
import json
import time

from odoo import api, fields, models

from odoo.exceptions import UserError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.api import ShopeeAPI
from base64 import b64decode

from psycopg2 import extensions
import logging

_logger = logging.getLogger(__name__)

class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    def shopee_get_order_list_query(self):
        self.ensure_one()
        sp_account = self.shopee_get_account()
        api = ShopeeAPI(sp_account)
        # Get Order List
        order_data_raw = []
        from_timestamp = api.to_api_timestamp(datetime(2022, 6, 1))
        to_timestamp = api.to_api_timestamp(datetime(2022, 6, 15))
        params = {
            'time_range_field': 'update_time',
            'time_from': from_timestamp,
            'time_to': to_timestamp,
            'response_optional_fields': 'order_status'
        }
        unlimited = True
        if unlimited:
            cursor = ""
            while unlimited:
                params.update({
                    'page_size': 100,
                    'cursor': cursor
                })
                prepared_request = api.build_request('order_list',
                                                     sp_account.partner_id,
                                                     sp_account.partner_key,
                                                     sp_account.shop_id,
                                                     sp_account.host,
                                                     sp_account.access_token,
                                                     ** {
                                                         'params': params
                                                     })
                response_data = api.process_response('order_list', api.request(**prepared_request))
                if response_data['order_list']:
                    order_data_raw.extend(response_data['order_list'])
                    if not response_data['next_cursor']:
                        unlimited = False
                    else:
                        cursor = response_data['next_cursor']
                else:
                    unlimited = False
        return order_data_raw

    def shopee_get_orders_detail_test(self, order_ids):
        order = self.env['ir.config_parameter'].sudo().get_param('mp.test.sp.order')
        if not order:
            raise UserError('Set order template in mp.test.sp.order in system parameter!')
        order_template = eval(order)
        order_list = []
        for order_id in order_ids:
            order_vals = order_template.copy()
            order_vals.update({
                'order_sn': order_id,
            })
            order_list.append(order_vals)
        return {
            'order_list': order_list,
        }

    def shopee_update_orders_status_query(self, limit=50, default_sp_order_status=False):
        self.ensure_one()
        sp_account = self.shopee_get_account()
        api = ShopeeAPI(sp_account)
        api_v1 = ShopeeAPI(sp_account, api_version="v1")

        default_sp_order_status_query = ''' sp_order_status NOT IN ('READY_TO_SHIP', 'UNPAID') '''
        if default_sp_order_status:
            default_sp_order_status_query = ''' sp_order_status = '%s' ''' % (default_sp_order_status)
        query = '''
            SELECT
                mp_invoice_number, sp_order_status
            FROM mp_webhook_order
            WHERE mp_account_id = %s
            AND is_process = false
            AND %s
            ORDER BY write_date ASC
            LIMIT %s
        ''' % (str(self.id), default_sp_order_status_query, str(limit))
        self.env.cr.execute(query)
        webhook_orders = self.env.cr.dictfetchall()
        mp_invoice_numbers = [("'%s'" % (order['mp_invoice_number'])) for order in webhook_orders]
        mp_invoice_numbers_query = ','.join(mp_invoice_numbers)
        mp_invoice_numbers_query = '(%s)' % mp_invoice_numbers_query
        # _logger.info('SHOPEE_UPDATE_QUERY > Start Webhook %s' % mp_invoice_numbers_query)

        if mp_invoice_numbers:
            query = '''
                UPDATE mp_webhook_order
                SET is_process = true
                WHERE mp_invoice_number in %s
            ''' % (mp_invoice_numbers_query)
            self.env.cr.execute(query)
            self.env.cr.commit()

            query = '''
                SELECT id, mp_invoice_number, sp_package_number, mp_order_status, raw
                FROM sale_order
                WHERE mp_invoice_number in %s
            ''' % (mp_invoice_numbers_query)
            self.env.cr.execute(query)
            sale_orders = self.env.cr.dictfetchall()
            sale_orders_by_mp_invoice_number = {}
            for sale_order in sale_orders:
                sale_orders_by_mp_invoice_number[sale_order['mp_invoice_number']] = sale_order

        for order in webhook_orders:
            try:
                if order['mp_invoice_number'] in sale_orders_by_mp_invoice_number:
                    sale_order = sale_orders_by_mp_invoice_number[order['mp_invoice_number']]
                else:
                    raise UserError('Sale Order Not Found')

                # MP Order Status
                sp_order_statuses = {
                    'waiting': ['UNPAID'],
                    'to_cancel': ['IN_CANCEL'],
                    'cancel': ['CANCELLED'],
                    'to_process': [],
                    'in_process': ['READY_TO_SHIP', 'RETRY_SHIP'],
                    'to_ship': ['PROCESSED'],
                    'in_ship': ['SHIPPED'],
                    'delivered': ['TO_CONFIRM_RECEIVE'],
                    'done': ['COMPLETED'],
                    'return': ['TO_RETURN']
                }
                sp_order_status = order['sp_order_status']
                mp_order_status = sale_order['mp_order_status']
                for key in sp_order_statuses:
                    if sp_order_status in sp_order_statuses[key]:
                        mp_order_status = key
                        break

                # Hit API Get Shipping Document Info
                if order['sp_order_status'] == 'PROCESSED':
                    # _logger.info('SHOPEE_UPDATE_QUERY > Status Order: PROCESSED')
                    params = {
                        'order_sn': sale_order['mp_invoice_number'],
                        'package_number': sale_order['sp_package_number']
                    }
                    prepared_request = api.build_request('shipping_doc_info',
                                                            sp_account.partner_id,
                                                            sp_account.partner_key,
                                                            sp_account.shop_id,
                                                            sp_account.host,
                                                            sp_account.access_token,
                                                            ** {
                                                                'params': params
                                                            })
                    response = api.process_response('shipping_doc_info', api.request(
                        **prepared_request), no_sanitize=True, no_validate=True)
                    if response.status_code == 200:
                        raw_data = response.json()
                        if 'error' in raw_data and raw_data['error']:
                            pass
                        else:
                            mp_awb_number =  raw_data['response']['shipping_document_info']['tracking_number']
                            query = '''
                                UPDATE sale_order
                                SET mp_awb_number = '%s',
                                    mp_order_status = '%s',
                                    sp_order_status = '%s'
                                WHERE id = %s
                            ''' % (mp_awb_number, mp_order_status, sp_order_status, sale_order['id'])
                            self.env.cr.execute(query)
                            # _logger.info('SHOPEE_UPDATE_QUERY > Status Order: PROCESSED. mp_awb_number %s' % (mp_awb_number))
                    else:
                        pass

                # Hit API Get Order Income
                elif order['sp_order_status'] == 'COMPLETED':
                    # _logger.info('SHOPEE_UPDATE_QUERY > Status Order: COMPLETED')
                    # body_income = {
                    #     'ordersn': sale_order['mp_invoice_number'],
                    # }
                    # prepared_request = api_v1.build_request('get_my_income',
                    #                                         sp_account.partner_id,
                    #                                         sp_account.partner_key,
                    #                                         sp_account.shop_id,
                    #                                         sp_account.host,
                    #                                         ** {
                    #                                             'json': body_income
                    #                                         })
                    # response = api_v1.process_response(
                    #     'get_my_income', api_v1.request(**prepared_request), no_sanitize=True)
                    body_income = {
                        'order_sn': sale_order['mp_invoice_number'],
                    }
                    prepared_request = api.build_request('get_my_income',
                                                            sp_account.partner_id,
                                                            sp_account.partner_key,
                                                            sp_account.shop_id,
                                                            sp_account.host,
                                                            **{
                                                                'json': body_income
                                                            })
                    response = api_v1.process_response(
                        'get_my_income', api.request(**prepared_request), no_sanitize=True)
                    if response.status_code == 200:
                        raw_data = response.json()
                        order_income = raw_data.get('order_income').get('escrow_amount')
                        try:
                            sale_order_raw = eval(sale_order['raw'])
                        except:
                            sale_order_raw = json.loads(sale_order['raw'])
                        sale_order_raw.update({
                            'order_income': raw_data.get('order_income'),
                        })
                        sale_order_raw = json.dumps(sale_order_raw, indent=4)
                        query = '''
                            UPDATE sale_order
                            SET mp_expected_income = %s,
                                mp_order_status = '%s',
                                sp_order_status = '%s',
                                raw = '%s'
                            WHERE id = %s
                        ''' % (order_income, mp_order_status, sp_order_status, sale_order_raw, sale_order['id'])
                        self.env.cr.execute(query)
                        # _logger.info('SHOPEE_UPDATE_QUERY > Status Order: COMPLETED. mp_expected_income %s' % (order_income))
                # Cancelled
                elif order['sp_order_status'] == 'CANCELLED':
                    sale_order_record = self.env['sale.order'].browse(sale_order['id'])
                    sale_order_record.action_cancel()
                    query = '''
                        UPDATE sale_order
                        SET mp_order_status = '%s',
                            sp_order_status = '%s'
                        WHERE id = %s
                    ''' % (mp_order_status, sp_order_status, sale_order['id'])
                    self.env.cr.execute(query)
                else:
                    # Update Status
                    query = '''
                        UPDATE sale_order
                        SET mp_order_status = '%s',
                            sp_order_status = '%s'
                        WHERE id = %s
                    ''' % (mp_order_status, sp_order_status, sale_order['id'])
                    self.env.cr.execute(query)
                # Commit
                self.env.cr.commit()
                # _logger.info('SHOPEE_UPDATE_QUERY > Finish An Order')
            except Exception as e:
                self.env.cr.rollback()
                # _logger.info('SHOPEE_UPDATE_QUERY > Failed %s' % str(e))

    def shopee_get_orders_query(self, limit=50):
        self.ensure_one()
        webhook_order_obj = self.env['mp.webhook.order']
        order_not_process = webhook_order_obj.search(
            [('mp_account_id', '=', self.id),
             ('is_process', '=', False),
             ('sp_order_status', '=', 'READY_TO_SHIP')], order='write_date', limit=limit)
        order_not_process.is_process = True
        self.env.cr.commit()

        all_order_ids = []
        for order in order_not_process:
            if order.mp_invoice_number not in all_order_ids:
                all_order_ids.append(order.mp_invoice_number)
        self.shopee_api_orders_query(all_order_ids)

    def shopee_retry_orders_query(self, limit=50):
        self.ensure_one()
        mp_log_error_obj = self.env['mp.log.error'].sudo()
        mp_logs = mp_log_error_obj.search(
            [('mp_account_id', '=', self.id),
             ('model_name', '=', 'sale.order'),
             ('mp_log_status', '=', 'failed'),
             ('mp_external_id', '!=', False)], order='write_date', limit=limit)

        all_order_ids = []
        for mp_log in mp_logs:
            if mp_log.mp_external_id not in all_order_ids:
                all_order_ids.append(mp_log.mp_external_id)
        self.shopee_api_orders_query(all_order_ids, retry=True)

    def shopee_api_orders_query(self, all_order_ids, retry=False):
        self.ensure_one()
        sp_account = self.shopee_get_account()
        api = ShopeeAPI(sp_account)
        api_v1 = ShopeeAPI(sp_account, api_version="v1")

        index = 0
        while index < len(all_order_ids):
            # _logger.info('SHOPEE_QUERY > Start Get Order Detail')
            order_ids = all_order_ids[index:index+50]
            index += 50
            # Get Order Detail
            # Check If Marketplace Test (mp.test)
            mp_test = self.env['ir.config_parameter'].sudo().get_param('mp.test')
            if mp_test:
                raw_data = self.shopee_get_orders_detail_test(order_ids)
            else:
                response_field = ['item_list', 'recipient_address', 'note,shipping_carrier', 'pay_time',
                                  'buyer_user_id', 'buyer_username', 'payment_method', 'package_list', 'actual_shipping_fee',
                                  'estimated_shipping_fee', 'actual_shipping_fee_confirmed', 'total_amount', 'cancel_reason',
                                  'checkout_shipping_carrier']
                params = {
                    'order_sn_list': ','.join(order_ids),
                    'response_optional_fields': ','.join(response_field)
                }
                prepared_request = api.build_request('order_detail',
                                                     sp_account.partner_id,
                                                     sp_account.partner_key,
                                                     sp_account.shop_id,
                                                     sp_account.host,
                                                     sp_account.access_token,
                                                     ** {
                                                         'params': params
                                                     })
                raw_data = api.process_response('order_detail', api.request(**prepared_request))

            # _logger.info('SHOPEE_QUERY > Finish Get Order Detail')
            for vals in raw_data['order_list']:
                # Hit API Get Shipping Paramaneter
                if vals['order_status'] in ['READY_TO_SHIP', 'PROCESSED']:
                    params = {
                        'order_sn': vals['order_sn'],
                    }
                    prepared_request = api.build_request('shipping_parameter',
                                                         sp_account.partner_id,
                                                         sp_account.partner_key,
                                                         sp_account.shop_id,
                                                         sp_account.host,
                                                         sp_account.access_token,
                                                         ** {
                                                             'params': params
                                                         })
                    response = api.process_response('shipping_parameter', api.request(
                        **prepared_request), no_sanitize=True, no_validate=True)
                    if response.status_code == 200:
                        raw_data = response.json()
                        if 'error' in raw_data and raw_data['error']:
                            pass
                        else:
                            vals.update({
                                'shipping_paramater': raw_data['response']
                            })
                    else:
                        pass

                try:
                    # _logger.info('SHOPEE_QUERY > Start An Order')
                    # Preparing Sales Order Value
                    query_vals = {
                        'state': 'draft',
                        'pricelist_id': self.pricelist_id.id,
                        'company_id': self.company_id.id,
                        'picking_policy': 'direct',
                        'warehouse_id': self.warehouse_id.id,
                        'marketplace': 'shopee',
                        'mp_account_id': self.id,
                        'raw': json.dumps(vals, indent=4),
                        'mp_invoice_number': vals.get('order_sn'),
                        'mp_external_id': vals.get('order_sn'),
                        'sp_order_id': vals.get('order_sn'),
                        'sp_order_status': vals.get('order_status'),
                        'mp_buyer_id': str(vals.get('buyer_user_id')),
                        'mp_buyer_username': vals.get('buyer_username'),
                        'mp_payment_method_info': vals.get('payment_method'),
                        'mp_delivery_carrier_name': vals.get('shipping_carrier'),
                        'mp_order_notes': vals.get('note'),
                        'mp_order_notes': vals.get('message_to_seller'),
                        'mp_cancel_reason': vals.get('cancel_reason'),
                        'mp_recipient_address_city': vals.get('recipient_address').get('city'),
                        'mp_recipient_address_name': vals.get('recipient_address').get('name'),
                        'mp_recipient_address_district': vals.get('recipient_address').get('district'),
                        'mp_recipient_address_country': vals.get('recipient_address').get('region'),
                        'mp_recipient_address_zip': vals.get('recipient_address').get('zipcode'),
                        'mp_recipient_address_phone': vals.get('recipient_address').get('phone'),
                        'mp_recipient_address_state': vals.get('recipient_address').get('state'),
                        'mp_recipient_address_full': vals.get('recipient_address').get('full_address'),
                        'mp_amount_total': vals.get('total_amount'),
                        # 'mp_awb_url': vals.get('awb_url'),
                        'mp_expected_income': vals.get('order_income').get('escrow_amount') if vals.get('order_income') else None,
                        'mp_delivery_carrier_type': vals.get('checkout_shipping_carrier', None)
                    }

                    def _convert_timestamp_to_datetime(data):
                        if data:
                            return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        else:
                            return None

                    def _get_time_slot(data):
                        if data:
                            slot_time = data[0]['time_slot_list'][0]['date']
                            slot_time_format = datetime.fromtimestamp(time.mktime(time.gmtime(slot_time))).strftime(
                                DEFAULT_SERVER_DATETIME_FORMAT)
                            return slot_time_format
                        else:
                            return None

                    def _get_package_number(data):
                        if data:
                            return data[0]['package_number']
                        else:
                            return None

                    def _get_tracking_number(data):
                        if data:
                            return data['tracking_number']
                        else:
                            return None

                    def _set_mp_delivery_type(data):
                        if data:
                            mp_delivery_type = None
                            if 'pickup' in data and 'dropoff' in data:
                                mp_delivery_type = 'both'
                            elif 'pickup' in data:
                                mp_delivery_type = 'pickup'
                            elif 'dropoff' in data:
                                mp_delivery_type = 'drop off'
                            return mp_delivery_type
                        else:
                            return None

                    def _handle_preorder(data):
                        if data:
                            if data != 2:
                                return True
                            else:
                                return False
                        return None

                    # Name
                    date_order = _convert_timestamp_to_datetime(vals.get('create_time'))
                    seq_date = None
                    if date_order:
                        seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(date_order))
                    name = self.env['ir.sequence'].next_by_code('sale.order', sequence_date=seq_date) or '/'

                    # Sale Channel
                    self.env.cr.execute('''
                        SELECT id
                        FROM sale_channel
                        WHERE mp_account_id = %s
                    ''' % (self.id))
                    channel = self.env.cr.dictfetchall()
                    if not channel:
                        raise UserError('Sale Channel Not Found')
                    channel_id = channel[0]['id']

                    # _logger.info('SHOPEE_QUERY > Order Name Channel')
                    # MP Order Status
                    sp_order_statuses = {
                        'waiting': ['UNPAID'],
                        'to_cancel': ['IN_CANCEL'],
                        'cancel': ['CANCELLED'],
                        'to_process': [],
                        'in_process': ['READY_TO_SHIP', 'RETRY_SHIP'],
                        'to_ship': ['PROCESSED'],
                        'in_ship': ['SHIPPED'],
                        'delivered': ['TO_CONFIRM_RECEIVE'],
                        'done': ['COMPLETED'],
                        'return': ['TO_RETURN']
                    }
                    sp_order_status = vals.get('order_status')
                    mp_order_status = 'waiting'
                    for key in sp_order_statuses:
                        if sp_order_status in sp_order_statuses[key]:
                            mp_order_status = key
                            break

                    query_vals.update({
                        'name': name,
                        'mp_order_status': mp_order_status,
                        'sale_channel_id': channel_id,
                        'mp_payment_date': _convert_timestamp_to_datetime(vals.get('pay_time')),
                        'mp_order_date': _convert_timestamp_to_datetime(vals.get('create_time')),
                        'create_date': _convert_timestamp_to_datetime(vals.get('create_time')),
                        'date_order': date_order,
                        'mp_order_last_update_date': _convert_timestamp_to_datetime(vals.get('update_time')),
                        'mp_shipping_deadline': _convert_timestamp_to_datetime(vals.get('ship_by_date')),
                        'sp_package_number': _get_package_number(vals.get('package_list')),
                        'is_preorder': _handle_preorder(vals.get('days_to_ship')),
                        'mp_awb_number': _get_tracking_number(vals.get('shipping_document_info')),
                        'mp_delivery_type': _set_mp_delivery_type(vals.get('shipping_paramater').get('info_needed')) if vals.get('shipping_paramater') else None,
                        'mp_pickup_time_slot': _set_mp_delivery_type(vals.get('shipping_paramater').get('pickup').get('address_list')) if vals.get('shipping_paramater') else None,
                    })

                    # Create Partner
                    self.env.cr.execute('''
                        SELECT id FROM res_partner
                        WHERE phone = '%s'
                        LIMIT 1
                    ''' % (query_vals.get('mp_recipient_address_phone')))
                    partners = self.env.cr.dictfetchall()
                    partner_id = False
                    if partners:
                        partner_id = partners[0]['id']
                    if not partner_id:
                        self.env.cr.execute('''
                            INSERT INTO res_partner (type, name, display_name, phone, street, zip, active)
                            VALUES ('%s', '%s', '%s', '%s', '%s', '%s', TRUE)
                            RETURNING id
                        ''' % ('contact',
                               query_vals.get('mp_recipient_address_name'),
                               query_vals.get('mp_recipient_address_name'),
                               query_vals.get('mp_recipient_address_phone'),
                               query_vals.get('mp_recipient_address_full'),
                               query_vals.get('mp_recipient_address_zip'),
                               ))
                        partner_id = self.env.cr.fetchone()[0]

                    # Create Delivery Address
                    self.env.cr.execute('''
                        SELECT id, street FROM res_partner
                        WHERE phone = '%s'
                        AND parent_id = %s
                        AND type = 'delivery'
                    ''' % (query_vals.get('mp_recipient_address_phone'), partner_id))
                    addresses = self.env.cr.dictfetchall()
                    address_id = False
                    for address in addresses:
                        if address['street'] == query_vals.get('mp_recipient_address_full'):
                            address_id = address['id']
                            break
                    if not address_id:
                        self.env.cr.execute('''
                            INSERT INTO res_partner (type, parent_id, name, display_name, phone, street, zip, active)
                            VALUES ('%s', %s, '%s', '%s', '%s', '%s', '%s', TRUE)
                            RETURNING id
                        ''' % (
                            'delivery',
                            partner_id,
                            query_vals.get('mp_recipient_address_name'),
                            query_vals.get('mp_recipient_address_name'),
                            query_vals.get('mp_recipient_address_phone'),
                            query_vals.get('mp_recipient_address_full'),
                            query_vals.get('mp_recipient_address_zip'),))
                        address_id = self.env.cr.fetchone()[0]

                    # Create Sales Order
                    query_vals.update({
                        'partner_id': partner_id,
                        'partner_shipping_id': address_id,
                        'partner_invoice_id': address_id,
                    })
                    # _logger.info('SHOPEE_QUERY > Order Partner')
                    insert_query = 'INSERT INTO sale_order (%s) VALUES %s RETURNING id'
                    insert_query = self.env.cr.mogrify(insert_query, (extensions.AsIs(
                        ','.join(query_vals.keys())), tuple(query_vals.values())))
                    self.env.cr.execute(insert_query)
                    sale_id = self.env.cr.fetchone()[0]
                    amount_untaxed = 0
                    amount_tax = 0
                    amount_total = 0
                    # _logger.info('SHOPEE_QUERY > Order Created')

                    # Create Sales Order Line
                    for item_vals in vals['item_list']:
                        product_uom_qty = item_vals.get('model_quantity_purchased')
                        query_item_vals = {
                            'order_id': sale_id,
                            'product_uom_qty': item_vals.get('model_quantity_purchased'),
                        }

                        def _handle_product_sku(data):
                            sku = None
                            if data['item_sku']:
                                sku = data['item_sku']
                            if data['model_sku']:
                                sku = data['model_sku']
                            return sku

                        def _handle_item_name(data):
                            name = None
                            if data['model_name']:
                                name = '%s (%s)' % (data['item_name'], data['model_name'])
                            else:
                                name = '%s' % (data['item_name'])
                            return name

                        def _handle_item_sku(data):
                            name = None
                            if data['model_sku']:
                                return data['model_sku']
                            else:
                                return data['item_sku']

                        def _handle_product_id(data):
                            product_id = False
                            item_id = data.get('item_id', False)
                            model_id = data.get('model_id', False)
                            if model_id:
                                self.env.cr.execute('''
                                    SELECT mmpl.product_id
                                    FROM mp_map_product_line mmpl
                                    LEFT JOIN mp_product_variant mppv ON (mppv.id = mmpl.mp_product_variant_id)
                                    WHERE mmpl.mp_account_id = %s
                                    AND mppv.mp_external_id = '%s'
                                    LIMIT 1
                                ''' % (self.id, model_id))
                                product = self.env.cr.dictfetchall()
                                product_id = False
                                if product:
                                    product_id = product[0]['product_id']
                            elif item_id:
                                self.env.cr.execute('''
                                    SELECT mmpl.product_id
                                    FROM mp_map_product_line mmpl
                                    LEFT JOIN mp_product mpp ON (mpp.id = mmpl.mp_product_id)
                                    WHERE mmpl.mp_account_id = %s
                                    AND mpp.mp_external_id = '%s'
                                    LIMIT 1
                                ''' % (self.id, item_id))
                                product = self.env.cr.dictfetchall()
                                product_id = False
                                if product:
                                    product_id = product[0]['product_id']
                            return product_id

                        def _handle_price_unit(data):
                            if data['model_discounted_price'] == 0 and data['promotion_type'] == 'bundle_deal':
                                promotion = self.env['mp.promotion.program'].sudo().search(
                                    [('mp_external_id', '=', str(data['promotion_id']))], limit=1)
                                if promotion.exists():
                                    if promotion.sp_bundle_discount_percentage > 0:
                                        discount_price = data['model_original_price'] * \
                                            promotion.sp_bundle_discount_percentage/100
                                        final_discounted_price = data['model_original_price'] - discount_price
                                        return final_discounted_price
                                    elif promotion.sp_bundle_discount_value > 0:
                                        final_discounted_price = data['model_original_price'] - \
                                            promotion.sp_bundle_discount_value
                                        return final_discounted_price
                                    elif promotion.sp_bundle_fix_price > 0:
                                        return promotion.sp_bundle_fix_price
                                else:
                                    return data['model_discounted_price']
                            else:
                                return data['model_discounted_price']

                        price_unit = _handle_price_unit(item_vals)
                        product_id = _handle_product_id(item_vals)
                        if not product_id:
                            raise UserError('Product Not Found [%s] %s' % (_handle_item_sku(item_vals), _handle_item_name(item_vals)))
                        self.env.cr.execute('''
                            SELECT pt.id, pt.name, pt.uom_id
                            FROM product_product pp
                            LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
                            WHERE pp.id = %s
                        ''' % (product_id))
                        product = self.env.cr.dictfetchall()
                        if not product:
                            raise UserError('Product Template Not Found')
                        product_template_id = product[0]['id']
                        product_name = product[0]['name']
                        product_uom = product[0]['uom_id']
                        query_item_vals.update({
                            'product_id': product_id,
                            'mp_product_name': _handle_item_name(item_vals),
                            'mp_product_sku': _handle_item_sku(item_vals),
                            'price_unit': price_unit,
                            'price_retail': item_vals.get('model_original_price'),
                            'price_discount': item_vals.get('model_original_price') - price_unit,
                            'product_uom': product_uom,
                            'name': product_name,
                            'customer_lead': 1,
                            'raw': json.dumps(item_vals, indent=4),
                            'mp_account_id': self.id,
                        })
                        insert_query = 'INSERT INTO sale_order_line (%s) VALUES %s RETURNING id'
                        insert_query = self.env.cr.mogrify(insert_query, (extensions.AsIs(
                            ','.join(query_item_vals.keys())), tuple(query_item_vals.values())))
                        self.env.cr.execute(insert_query)
                        sale_line_id = self.env.cr.fetchone()[0]
                        # _logger.info('SHOPEE_QUERY > Order Line Created')

                        # Compute Amount & Tax
                        self.env.cr.execute('''
                            SELECT tax_id
                            FROM product_taxes_rel
                            WHERE prod_id = %s
                        ''' % (product_template_id))
                        taxes = self.env.cr.dictfetchall()
                        for tax in taxes:
                            self.env.cr.execute('''
                                INSERT INTO account_tax_sale_order_line_rel
                                (sale_order_line_id, account_tax_id)
                                VALUES (%s, %s)
                            ''' % (sale_line_id, tax['tax_id']))

                        # Compute Tax
                        tax = self.env['account.tax'].browse(tax['tax_id'])
                        currency = self.env.ref('base.IDR')
                        taxes = tax.compute_all(price_unit, currency, product_uom_qty)
                        price_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                        price_total = taxes['total_included']
                        price_subtotal = taxes['total_excluded']
                        self.env.cr.execute('''
                            UPDATE sale_order_line
                            SET price_tax = %s, price_total = %s, price_subtotal = %s
                            WHERE id = %s
                        ''' % (price_tax, price_total, price_subtotal, sale_line_id))

                        # Compute Order
                        amount_untaxed += price_subtotal
                        amount_tax += price_tax
                        amount_total += (price_subtotal + price_tax)
                        # _logger.info('SHOPEE_QUERY > Amount Calculation')

                    # Update Amount Order
                    self.env.cr.execute('''
                        UPDATE sale_order
                        SET amount_untaxed = %s, amount_tax = %s, amount_total = %s
                        WHERE id = %s
                    ''' % (amount_untaxed, amount_tax, amount_total, sale_id))
                    # Update Log
                    if retry:
                        self.env.cr.execute('''
                            UPDATE mp_log_error
                            SET mp_log_status = 'success'
                            WHERE mp_external_id = '%s' AND mp_account_id = %s
                        ''' % (vals['order_sn'], self.id))
                    self.env.cr.commit()
                    # _logger.info('SHOPEE_QUERY > Finish An Order')
                except Exception as e:
                    self.env.cr.rollback()
                    if not retry:
                        mp_log_error_obj = self.env['mp.log.error'].sudo()
                        log_values = {
                            'name': 'Error Create Sales Order',
                            'model_name': 'sale.order',
                            'mp_log_status': 'failed',
                            'notes': str(e),
                            'mp_external_id': vals['order_sn'],
                            'mp_account_id': self.id,
                            'last_retry_time': fields.Datetime.now(),
                        }
                        mp_log_error_obj.create(log_values)
                        self.env.cr.commit()
                    # _logger.info('SHOPEE_QUERY > Failed %s' % str(e))
