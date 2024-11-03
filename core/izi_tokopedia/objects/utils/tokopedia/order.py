# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time
from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta

from requests import PreparedRequest

from .api import TokopediaAPI


class TokopediaOrder(TokopediaAPI):

    def __init__(self, tp_account, **kwargs):
        super(TokopediaOrder, self).__init__(tp_account, **kwargs)

    def datetime_convert_tz(self, dt, dt_tz, to_tz):
        dt_tz = pytz.timezone(dt_tz)
        to_tz = pytz.timezone(to_tz)
        return dt_tz.localize(dt).astimezone(to_tz)

    def get_order_list(self, *args, **kwargs):
        return getattr(self, '%s_get_order_list' % self.api_version)(*args, **kwargs)

    def v2_get_order_list(self, from_date, to_date, shop_id=None, limit=0, per_page=50):
        response_datas = []
        params = {
            'fs_id': self.tp_account.fs_id,
        }

        if shop_id:
            params.update({'shop_id': shop_id})

        date_ranges = self.pagination_datetime_range(from_date, to_date)
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])

            params.update({
                'from_date': from_timestamp,
                'to_date': to_timestamp
            })

            if limit > 0 and limit == len(response_datas):
                break

            unlimited = not limit
            if unlimited:
                page = 1
                while unlimited:
                    params.update({
                        'page': page,
                        'per_page': per_page
                    })
                    prepared_request = self.build_request('order_list', params=params)
                    response = self.request(**prepared_request)
                    response_data = self.process_response('default', response)
                    if response_data:
                        response_datas.extend(response_data)
                        # self._logger.info("Order: Imported %d record(s) of unlimited." % len(response_datas))
                        page += 1
                    else:
                        unlimited = False
            else:
                pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
                for pagination_page in pagination_pages:
                    params.update({
                        'page': pagination_page[0],
                        'per_page': pagination_page[1]
                    })
                    prepared_request = self.build_request('order_list', params=params)
                    response = self.request(**prepared_request)
                    response_data = self.process_response('order_list', response)
                    if response_data:
                        response_datas.extend(response_data)
                        # if limit == 1:
                        #     self._logger.info("Order: Imported 1 record.")
                        # else:
                        #     self._logger.info("Order: Imported %d record(s) of %d." % (len(response_datas), limit))

        # self._logger.info("Order: Finished %d record(s) imported." % len(response_datas))
        return response_datas

    def get_order_detail(self, *args, **kwargs):
        return getattr(self, '%s_get_order_detail' % self.api_version)(*args, **kwargs)

    def v2_get_order_detail(self, order_ids=None, invoice_num_ids=None, show_log=False, **kwargs):
        params = {}
        order_data = []

        def process_order_detail(**payload):
            prepared_request = self.build_request('order_detail', params=payload)
            response = self.request(**prepared_request)
            tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
            if tp_limit_rate_reset > 0:
                # self._logger.info(
                #     "Order: Too many requests, Tokopedia asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
                time.sleep(tp_limit_rate_reset + 1)
            return self.process_response('order_detail', response)

        def process_order_summary(shop_id, tp_data_detail_order):
            # Get order summary
            tp_order_create_time = datetime.fromisoformat(tp_data_detail_order['payment_date'][:-1].split('.')[0])
            tp_order_create_time_utc = self.datetime_convert_tz(tp_order_create_time, 'Asia/Jakarta', 'UTC')
            order_summary_params = {
                'from_date': tp_order_create_time_utc.replace(tzinfo=None) - relativedelta(minutes=1),
                'to_date': tp_order_create_time_utc.replace(tzinfo=None) + relativedelta(minutes=1),
                'shop_id': shop_id,
            }
            tp_data_orders = self.get_order_list(**order_summary_params)
            if tp_data_orders:
                tp_data_order = list(filter(lambda o: o['invoice_ref_num'] ==
                                     tp_data_detail_order['invoice_number'], tp_data_orders))[0]
                tp_data_detail_order.update({'order_summary': tp_data_order})
            else:
                tp_data_detail_order.update({'order_summary': []})
            return tp_data_detail_order
        # print('order_ids: %s' % order_ids)
        if not order_ids and not invoice_num_ids:
            raise ValueError("Params is required, please input order_id or invoice_num!")

        index = 0
        if invoice_num_ids:
            for inv in invoice_num_ids:
                index += 1
                # if show_log:
                #     self._logger.info(
                #         "Order: (%s/%s) Getting order detail of %s... Please wait!" % (index, len(invoice_num_ids), inv))
                params.update({
                    'invoice_num': inv,
                })
                response = process_order_detail(**params)
                if kwargs.get('get_order_summary', False):
                    response = process_order_summary(kwargs.get('shop_id'), response)
                order_data.append(response)

        elif order_ids:
            for order_id in order_ids:
                index += 1
                # if show_log:
                #     self._logger.info(
                #         "Order: (%s/%s) Getting order detail of %s... Please wait!" % (index, len(order_ids), order_id))
                params.update({
                    'order_id': order_id,
                })
                response = process_order_detail(**params)
                if kwargs.get('get_order_summary', False):
                    response = process_order_summary(kwargs.get('shop_id'), response)
                order_data.append(response)

        return order_data

    def action_accept_order(self, *args, **kwargs):
        return getattr(self, '%s_action_accept_order' % self.api_version)(*args, **kwargs)

    def v1_action_accept_order(self, order_id):
        self.endpoints.tp_account.order_id = order_id
        prepared_request = self.build_request('order_accept', params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_reject_order(self, *args, **kwargs):
        return getattr(self, '%s_action_reject_order' % self.api_version)(*args, **kwargs)

    def v1_action_reject_order(self, order_id, reason_code, reason, **kwargs):
        self.endpoints.tp_account.order_id = order_id

        reason_code = int(reason_code)
        data = {
            'reason_code': reason_code,
            'reason': reason
        }

        if reason_code == 4:
            if not kwargs.get('shop_close_end_date') or not kwargs.get('shop_close_note'):
                raise TypeError("shop_close_end_date and shop_close_not is mandatory!")

            data.update({
                'shop_close_end_date': kwargs.get('shop_close_end_date'),
                'shop_close_note': kwargs.get('shop_close_note')
            })

        prepared_request = self.build_request('order_reject', json=data, params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_get_shipping_label(self, *args, **kwargs):
        return getattr(self, '%s_action_get_shipping_label' % self.api_version)(*args, **kwargs)

    def v1_action_get_shipping_label(self, order_id, printed=0):
        self.endpoints.tp_account.order_id = order_id

        params = {'printed': printed}

        prepared_request = self.build_request('order_shipping_label', params=params)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response, no_sanitize=True)
        return response_data

    def action_print_shipping_label(self, *args, **kwargs):
        return getattr(self, '%s_action_print_shipping_label' % self.api_version)(*args, **kwargs)

    def url_action_print_shipping_label(self, order_ids, printed=0):
        if not isinstance(order_ids, list):
            raise TypeError("order_ids should be in list format!")

        if not order_ids:
            raise TypeError("order_ids can not be empty!")

        params = {
            'order_id': ','.join(order_ids),
            'mark_as_printed': printed
        }

        url = self.endpoints.get_url('order_shipping_label')
        prepared_request_obj = PreparedRequest()
        prepared_request_obj.prepare_url(url, params)
        return prepared_request_obj.url

    def action_get_booking_code(self, *args, **kwargs):
        return getattr(self, '%s_action_get_booking_code' % self.api_version)(*args, **kwargs)

    def v1_action_get_booking_code(self, order_id=None):
        params = {}

        if order_id:
            params.update({'order_id': order_id})

        prepared_request = self.build_request('fulfillment_order', params=params)
        response = self.request(**prepared_request)
        response_data = self.process_response('booking_code', response)
        return response_data

    def action_confirm_shipping(self, *args, **kwargs):
        return getattr(self, '%s_action_confirm_shipping' % self.api_version)(*args, **kwargs)

    def v1_action_confirm_shipping(self, order_id, order_status, shipping_ref_num, **kwargs):
        self.endpoints.tp_account.order_id = order_id

        data = {
            'order_status': order_status,
            'shipping_ref_num': shipping_ref_num
        }

        prepared_request = self.build_request('confirm_shipping', json=data, params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_request_pickup(self, *args, **kwargs):
        return getattr(self, '%s_action_request_pickup' % self.api_version)(*args, **kwargs)

    def v1_action_request_pickup(self, order_id, shop_id):
        data = {
            'order_id': int(order_id),
            'shop_id': int(shop_id)
        }
        prepared_request = self.build_request('request_pickup', json=data, params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def action_update_shipping_number(self, *args, **kwargs):
        return getattr(self, '%s_action_update_shipping_number' % self.api_version)(*args, **kwargs)

    def v1_action_update_shipping_number(self, order_id, shipping_number):
        data = {
            'order_id': int(order_id),
            'order_status': 500,
            'shipping_ref_num': shipping_number
        }
        prepared_request = self.build_request('update_shipping_number', json=data, params={}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data