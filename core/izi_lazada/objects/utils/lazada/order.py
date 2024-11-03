# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from itertools import count
from .api import LazadaAPI


class LazadaOrder(LazadaAPI):

    def __init__(self, lz_account, **kwargs):
        super(LazadaOrder, self).__init__(lz_account, **kwargs)
        self.order_data = []
        self.order_data_raw = []

    def get_order_items(self, datas=[], per_page=100):
        order_list_split = [datas[x:x+per_page] for x in range(0, len(datas), per_page)]
        count_order = 0

        lz_order_by_orderid = {}
        for lz_order in datas:
            lz_order_by_orderid[lz_order['order_id']] = lz_order

        for order in order_list_split:
            order_id_list = []
            for order_id in order:
                order_id_list.append(order_id['order_id'])
            count_order += len(order_id_list)
            self._logger.info("Order: Get order items %d of %d." % (count_order, len(datas)))
            params = {
                'order_ids': str(order_id_list)
            }
            lz_request = self.endpoints.build_lz_request('orders_item', **{'force_params': True, 'params': params})
            lz_client = self.lz_account.lz_client
            lz_order_raw = self.process_response(
                'orders_item', lz_client.execute(lz_request, self.lz_account.access_token))
            for index, order_raw in enumerate(lz_order_raw):
                self._logger.info("Order: Processing order items %d of %d." % (index+1, len(lz_order_raw)))
                order_line = {}
                lz_order = lz_order_by_orderid[order_raw['order_id']]
                lz_order['order_line'] = []
                for order_item in order_raw['order_items']:
                    order_item['qty'] = 1
                    if order_item['sku_id'] not in order_line:
                        order_line[order_item['sku_id']] = order_item
                        order_line[order_item['sku_id']]['order_item_ids'] = str(order_item['order_item_id'])
                    else:
                        order_line[order_item['sku_id']]['paid_price'] += order_item['paid_price']
                        order_line[order_item['sku_id']]['item_price'] += order_item['item_price']
                        order_line[order_item['sku_id']]['shipping_fee_original'] += order_item['shipping_fee_original']
                        order_line[order_item['sku_id']]['shipping_amount'] += order_item['shipping_amount']
                        order_line[order_item['sku_id']]['qty'] += 1
                        order_line[order_item['sku_id']]['order_item_ids'] = str(
                            order_line[order_item['sku_id']]['order_item_id'])+','+str(order_item['order_item_id'])
                for line in order_line:
                    lz_order['order_line'].append(order_line[line])

                lz_order.update({
                    'invoice_number': lz_order['order_line'][0]['invoice_number'],
                    'tracking_code': lz_order['order_line'][0]['tracking_code'],
                    'package_id': lz_order['order_line'][0]['package_id'],
                    'sla_time_stamp': lz_order['order_line'][0]['sla_time_stamp'],
                    'reason': lz_order['order_line'][0]['reason'],
                    'shipping_info': {
                        'shipping_type': lz_order['order_line'][0]['shipping_type'],
                        'shipment_provider': lz_order['order_line'][0]['shipment_provider'],
                        'shipping_provider_type': lz_order['order_line'][0]['shipping_provider_type'],
                        'promised_shipping_time': lz_order['order_line'][0]['promised_shipping_time'],
                    },
                })

        return datas

    def get_order_list(self, from_date, to_date, limit=0, per_page=100, time_mode=None, **kwargs):
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        lz_order_data = []
        for date_range in date_ranges:
            date_after = date_range[0].astimezone(self.lz_account.api_tz).isoformat()
            date_before = date_range[1].astimezone(self.lz_account.api_tz).isoformat()
            time_mode = time_mode.split('_')[0]
            if time_mode == 'create':
                params = {
                    time_mode+'d'+'_after': date_after,
                    time_mode+'d'+'_before': date_before,
                }
            else:
                params = {
                    time_mode+'_after': date_after,
                    time_mode+'_before': date_before,
                }
            unlimited = not limit
            if unlimited:
                offset = 0
                while unlimited:
                    params.update({
                        'offset': offset,
                        'limit': per_page,
                        'sort_direction': 'ASC'
                    })
                    lz_request = self.endpoints.build_lz_request(
                        'order_list', **{'force_params': True, 'params': params})
                    lz_client = self.lz_account.lz_client
                    lz_order_list_raw = self.process_response(
                        'order_list', lz_client.execute(lz_request, self.lz_account.access_token))

                    if 'orders' in lz_order_list_raw and lz_order_list_raw['orders']:
                        if lz_order_list_raw['countTotal'] != len(lz_order_data):
                            # lz_order_datas_raw = self.get_order_items(datas=lz_order_list_raw['orders'])
                            lz_order_data.extend(lz_order_list_raw['orders'])
                            offset += per_page
                        else:
                            unlimited = False
                    else:
                        unlimited = False
        self._logger.info("Order: Get Order List Finished %d imported." % len(lz_order_data))
        return lz_order_data

    def get_order(self, order_ids=[]):
        lz_order_data = []
        for order in order_ids:
            params = {
                'order_id': int(order)
            }
            lz_request = self.endpoints.build_lz_request(
                'order_detail', **{'force_params': True, 'params': params})
            lz_client = self.lz_account.lz_client
            lz_order_raw = self.process_response(
                'order_detail', lz_client.execute(lz_request, self.lz_account.access_token))
            if lz_order_raw:
                lz_order_data.append(lz_order_raw)

        return lz_order_data

    def action_pack_order(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'pack_order', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_pack_order = self.process_response(
            'pack_order', lz_client.execute(lz_request, self.lz_account.access_token))
        if lz_pack_order:
            return 'success'
        else:
            return 'failed'

    def action_set_invoice(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'set_invoice', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_set_invoice = self.process_response(
            'set_invoice', lz_client.execute(lz_request, self.lz_account.access_token))
        if lz_set_invoice:
            return 'success'
        else:
            return 'failed'

    def action_ready_to_ship(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'ready_to_ship', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_to_rts = self.process_response(
            'ready_to_ship', lz_client.execute(lz_request, self.lz_account.access_token))
        if lz_to_rts:
            return 'success'
        else:
            return 'failed'

    def action_repack(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'repack_order', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_repack = self.process_response(
            'repack_order', lz_client.execute(lz_request, self.lz_account.access_token))
        if lz_repack:
            return 'success'
        else:
            return 'failed'

    def action_delivery(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'set_delivery', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_repack = self.process_response(
            'set_delivery', lz_client.execute(lz_request, self.lz_account.access_token))
        if lz_repack:
            return 'success'
        else:
            return 'failed'

    def action_print_label(self, **kwargs):
        lz_request = self.endpoints.build_lz_request(
            'print_label', **{'force_params': True, 'params': kwargs})
        lz_client = self.lz_account.lz_client
        lz_response = self.process_response(
            'print_label', lz_client.execute(lz_request, self.lz_account.access_token))
        if 'document' in lz_response:
            return lz_response
        else:
            return False
