# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from .api import ShopeeAPI


class ShopeeOrder(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeOrder, self).__init__(sp_account, **kwargs)
        self.order_data = []
        self.order_data_raw = []

    def get_income(self, *args, **kwargs):
        return getattr(self, '%s_get_income' % self.api_version)(*args, **kwargs)

    def v1_get_income(self, **kwargs):
        body = {
            'ordersn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('get_my_income',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              ** {
                                                  'json': body
                                              })
        response = self.process_response('get_my_income', self.request(**prepared_request), no_sanitize=True)
        return response.json()

    def v2_get_income(self, **kwargs):
        body = {
            'order_sn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('get_my_income',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                   'json': body
                                              })
        response = self.process_response('get_my_income', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        if raw_data.get('response', False):
            return raw_data.get('response')
        return response.json()

    def get_airways_bill(self, **kwargs):
        return getattr(self, '%s_get_awb' % self.api_version)(**kwargs)

    def v1_get_awb(self, **kwargs):
        body = {
            'ordersn_list': [kwargs.get('order_sn')],
        }
        prepared_request = self.build_request('get_awb_url',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              ** {
                                                  'json': body
                                              })
        response = self.process_response('get_awb_url', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        awb_dict = {}
        if raw_data.get('result', False):
            for data in raw_data['result']['airway_bills']:
                awb_dict[data['ordersn']] = data['airway_bill']
        return awb_dict

    def get_shipping_parameter(self, **kwargs):
        return getattr(self, '%s_get_shipping_parameter' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                       })

    def v2_get_shipping_parameter(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('shipping_parameter',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('shipping_parameter', self.request(
            **prepared_request), no_sanitize=True, no_validate=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def get_shipping_doc_info(self, **kwargs):
        return getattr(self, '%s_get_shipping_doc_info' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                           'package_number': kwargs.get('package_number')
                       })

    def v2_get_shipping_doc_info(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
            'package_number': kwargs.get('package_number')
        }
        prepared_request = self.build_request('shipping_doc_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('shipping_doc_info', self.request(
            **prepared_request), no_sanitize=True, no_validate=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def get_order_detail(self, **kwargs):
        return getattr(self, '%s_get_order_detail' % self.api_version)(**kwargs)

    def v2_get_order_detail(self, **kwargs):
        def req_order_detail(order_ids):
            params = {
                'order_sn_list': ','.join(order_ids),
                'response_optional_fields': ','.join(response_field)
            }
            prepared_request = self.build_request('order_detail',
                                                  self.sp_account.partner_id,
                                                  self.sp_account.partner_key,
                                                  self.sp_account.shop_id,
                                                  self.sp_account.host,
                                                  self.sp_account.access_token,
                                                  ** {
                                                      'params': params
                                                  })
            raw_data = self.process_response('order_detail', self.request(**prepared_request))
            return raw_data['order_list']

        response_field = ['item_list', 'recipient_address', 'note,shipping_carrier', 'pay_time', 'pickup_done_time',
                          'buyer_user_id', 'buyer_username', 'payment_method', 'package_list', 'actual_shipping_fee',
                          'estimated_shipping_fee', 'actual_shipping_fee_confirmed', 'total_amount', 'cancel_reason',
                          'checkout_shipping_carrier']
        raw_datas = {'order_list': []}
        per_page = 50
        count_order = 0
        if kwargs.get('sp_data', False):
            sp_data = kwargs.get('sp_data')
            order_list_split = [sp_data[x:x+per_page] for x in range(0, len(sp_data), per_page)]
            for datas in order_list_split:
                order_id_list = []
                for order in datas:
                    order_id_list.append(order['order_sn'])
                count_order += len(order_id_list)
                # self._logger.info("Order: Get order detail %d of %d." % (count_order, len(sp_data)))
                raw_data = req_order_detail(order_id_list)
                raw_datas['order_list'].extend(raw_data)

        elif kwargs.get('order_ids', False):
            sp_data = kwargs.get('order_ids')
            order_list_split = [sp_data[x:x+per_page] for x in range(0, len(sp_data), per_page)]
            for datas in order_list_split:
                order_id_list = []
                for order in datas:
                    order_id_list.append(order)
                count_order += len(order_id_list)
                # self._logger.info("Order: Get order detail %d of %d." % (len(order_id_list), count_order))
                raw_data = req_order_detail(order_id_list)
                raw_datas['order_list'].extend(raw_data)

        temp_raw_data = raw_datas['order_list']
        for index, data in enumerate(temp_raw_data):
            shipping_parameter = False
            shipping_info = False
            shipping_tracking = {}
            # get shipping type
            if data['order_status'] in ['READY_TO_SHIP', 'PROCESSED', 'SHIPPED']:
                shipping_parameter = self.get_shipping_parameter(order_sn=data['order_sn'])
                # get shipping document info
                if data['order_status'] == 'PROCESSED' or data['order_status'] == 'SHIPPED':
                    # shipping_info = self.get_shipping_doc_info(
                    #     order_sn=data['order_sn'], package_number=data['package_list'][0]['package_number'])
                    shipping_info = self.get_tracking_number(
                        order_sn=data['order_sn'], package_number=data['package_list'][0]['package_number'])
                    if shipping_info:
                        # shipping_info = shipping_info['tracking_number']
                        shipping_tracking.update({
                            'tracking_number': shipping_info['tracking_number']
                        })

            raw_datas['order_list'][index].update({
                'shipping_paramater': shipping_parameter,
                # 'shipping_document_info': shipping_info
                'shipping_document_info': shipping_tracking
            })
        # self._logger.info("Order: Finished Get order detail %d record(s) imported." % len(raw_datas['order_list']))
        return raw_datas['order_list']

    def get_order_list(self, **kwargs):
        return getattr(self, '%s_get_order_list' % self.api_version)(**kwargs)

    def v2_get_order_list(self, from_date, to_date, limit=0, per_page=100, time_mode=None, **kwargs):
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])
            params = {
                'time_range_field': time_mode,
                'time_from': from_timestamp,
                'time_to': to_timestamp,
                'response_optional_fields': 'order_status'
            }
            unlimited = not limit
            if unlimited:
                cursor = ""
                while unlimited:
                    params.update({
                        'page_size': per_page,
                        'cursor': cursor
                    })
                    prepared_request = self.build_request('order_list',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.host,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'params': params
                                                          })
                    response_data = self.process_response('order_list', self.request(**prepared_request))
                    if response_data:
                        if 'order_list' in response_data and response_data['order_list']:
                            self.order_data_raw.extend(response_data['order_list'])
                            # self._logger.info("Order: Get order list %d of unlimited." % len(response_data['order_list']))
                            if not response_data['next_cursor']:
                                unlimited = False
                            else:
                                cursor = response_data['next_cursor']
                        else:
                            unlimited = False
                    else:
                        unlimited = False
        # self._logger.info("Order: Finished Get order List %d record(s) imported." % len(self.order_data_raw))
        # return self.order_data_raw, self.order_data
        return self.order_data_raw

    def action_ship_order(self, **kwargs):
        return getattr(self, '%s_ship_order' % self.api_version)(**kwargs)

    def v2_ship_order(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_sn'),
            # 'package_number': kwargs.get('package_number'),
        }
        if kwargs.get('dropoff', False):
            payload.update({'dropoff': kwargs.get('dropoff')})
        elif kwargs.get('pickup', False):
            payload.update({'pickup': kwargs.get('pickup')})
        prepared_request = self.build_request('ship_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('ship_order', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        if raw_data['error']:
            return 'failed'
        else:
            return 'success'

    def action_batch_ship_order(self, **kwargs):
        return getattr(self, '%s_batch_ship_order' % self.api_version)(**kwargs)

    def v2_batch_ship_order(self, **kwargs):
        prepared_request = self.build_request('batch_ship_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': kwargs
                                              })
        response = self.process_response('batch_ship_order', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        if raw_data['error']:
            return 'failed'
        else:
            return raw_data['response']

    def v1_batch_ship_order(self, **kwargs):
        prepared_request = self.build_request('batch_ship_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              ** {
                                                  'json': kwargs
                                              })
        response = self.process_response('batch_ship_order', self.request(**prepared_request), no_sanitize=True)
        raw_data = response.json()
        if raw_data['error']:
            return 'failed'
        else:
            return raw_data['response']

    def action_reject_order(self, **kwargs):
        return getattr(self, '%s_reject_order' % self.api_version)(**kwargs)

    def v2_reject_order(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_exid'),
            'cancel_reason': kwargs.get('reason_code')
        }
        if kwargs.get('item_list', False):
            payload.update({'item_list': kwargs.get('item_list')})

        prepared_request = self.build_request('reject_order',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('reject_order', self.request(**prepared_request), no_sanitize=True)
        # raw_data = response.json()
        # return raw_data['message']
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def action_handle_buyer_cancel(self, **kwargs):
        return getattr(self, '%s_handle_buyer_cancel' % self.api_version)(**kwargs)

    def v2_handle_buyer_cancel(self, **kwargs):
        payload = {
            'order_sn': kwargs.get('order_sn'),
            'operation': kwargs.get('operation')
        }

        prepared_request = self.build_request('buyer_cancellation',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('buyer_cancellation', self.request(**prepared_request))
        if response.get('update_time', False):
            return "success"
        else:
            return "fail"

    def get_awb_number(self, **kwargs):
        return getattr(self, '%s_get_awb_number' %
                       self.api_version)(**{
                           'order_sn': kwargs.get('order_sn'),
                       })

    def v2_get_awb_number(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
        }
        prepared_request = self.build_request('get_awb_num',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        raw_data = self.process_response('get_awb_num', self.request(**prepared_request))
        return raw_data

    def get_tracking_number(self, *args, **kwargs):
        return getattr(self, '%s_get_tracking_number' % self.api_version)(**{
                    'order_sn': kwargs.get('order_sn'),
                    'package_number': kwargs.get('package_number')
                })

    def v2_get_tracking_number(self, **kwargs):
        params = {
            'order_sn': kwargs.get('order_sn'),
            'package_number': kwargs.get('package_number') or ''
        }
        prepared_request = self.build_request('get_tracking_number',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_tracking_number', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def download_shipping_document(self, *args, **kwargs):
        return getattr(self, '%s_download_shipping_document' % self.api_version)(**{
                    'order_sn': kwargs.get('order_sn'),
                    'package_number': kwargs.get('package_number') or '',
                    'tracking_number': kwargs.get('tracking_number')
                })

    def v2_download_shipping_document(self, **kwargs):
        create_document = self.create_shipping_document(
            order_sn=kwargs.get('order_sn'), package_number=kwargs.get('package_number'), tracking_number=kwargs.get('tracking_number'))
        if create_document:
            status_document = self.get_shipping_document_status(order_sn=kwargs.get('order_sn'), package_number=kwargs.get('package_number'))
            if status_document:
                status = status_document['result_list'][0]['status']
                if status == 'READY':
                    params = {
                        'shipping_document_type': 'THERMAL_AIR_WAYBILL',
                        'order_list': [{
                            'order_sn': kwargs.get('order_sn'),
                            'package_number': kwargs.get('package_number')  or ''
                        }]
                    }
                    prepared_request = self.build_request('download_shipping_document',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.host,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'json': params
                                                          })
                    response = self.process_response('download_shipping_document', self.request(**prepared_request), no_sanitize=True)
                else:
                    response = {
                        'error': "document_not_ready",
                        'message': "Your document status is: %s. You can't download this document until the status is READY."
                    }
                return response

    def create_shipping_document(self, **kwargs):
        params = {
            'order_list': [{
                'order_sn': kwargs.get('order_sn'),
                'package_number': kwargs.get('package_number') or '',
                'tracking_number': kwargs.get('tracking_number'),
                'shipping_document_type': 'THERMAL_AIR_WAYBILL'
            }]
        }
        prepared_request = self.build_request('create_shipping_document',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': params
                                              })
        response = self.process_response('create_shipping_document', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def get_shipping_document_status(self, **kwargs):
        params = {
            'order_list': [{
                'order_sn': kwargs.get('order_sn'),
                'package_number': kwargs.get('package_number')  or '',
                'shipping_document_type': 'THERMAL_AIR_WAYBILL'
            }]
        }
        prepared_request = self.build_request('get_shipping_document_status',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': params
                                              })
        response = self.process_response('get_shipping_document_status', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()