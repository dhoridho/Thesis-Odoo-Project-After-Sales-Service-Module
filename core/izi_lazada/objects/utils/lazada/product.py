# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
# from dict2xml import dict2xml

from .api import LazadaAPI


class LazadaProduct(LazadaAPI):

    def __init__(self, lz_account, **kwargs):
        super(LazadaProduct, self).__init__(lz_account, **kwargs)
        self.product_data = []
        self.product_data_raw = []

    def get_product_detail(self, item_ids=[]):
        for item in item_ids:
            params = {
                'item_id': item
            }
            lz_request = self.endpoints.build_lz_request('product_detail', **{'force_params': True, 'params': params})
            lz_client = self.lz_account.lz_client
            lz_product_raw = self.process_response(
                'product_detail', lz_client.execute(lz_request, self.lz_account.access_token))
            self.product_data_raw.append(lz_product_raw)
        return self.product_data_raw

    def get_product_list(self, limit=0, per_page=50, **kwargs):
        params = {}
        lz_product_data = []
        unlimited = not limit
        if unlimited:
            offset = 0
            while unlimited:
                params.update({
                    'offset': offset,
                    'limit': per_page,
                    'filter': 'all'
                })
                lz_request = self.endpoints.build_lz_request('product_list', **{'force_params': True, 'params': params})
                lz_client = self.lz_account.lz_client
                lz_product_list_raw = self.process_response(
                    'product_list', lz_client.execute(lz_request, self.lz_account.access_token))
                if 'products' in lz_product_list_raw and lz_product_list_raw['products']:
                    lz_product_data.extend(lz_product_list_raw['products'])
                    self._logger.info("Product: Imported %d of %d imported." %
                                      (len(lz_product_list_raw['products']), len(lz_product_data)))
                    offset += len(lz_product_list_raw['products'])
                    # lz_product_data = self.get_product_detail(item_ids=item_ids)
                else:
                    unlimited = False
        self._logger.info("Product: Finished %d imported." % len(lz_product_data))
        return lz_product_data

    def update_product_price_qty(self, body={}):
        params = {
            'payload': dict2xml(body)
        }
        lz_request = self.endpoints.build_lz_request('product_price_qty', **{'force_params': True, 'params': params})
        lz_client = self.lz_account.lz_client
        lz_response = self.process_response(
            'product_price_qty', lz_client.execute(lz_request, self.lz_account.access_token), no_validate=True, no_sanitize=True)
        if lz_response.code == '0':
            return 'success'
        else:
            return lz_response.message
