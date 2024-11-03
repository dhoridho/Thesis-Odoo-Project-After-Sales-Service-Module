# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
from .api import TiktokAPI
import time

class TiktokCategory(TiktokAPI):

    def get_category_info(self, *args, **kwargs):
        return getattr(self, '%s_get_category_info' % self.api_version)(*args, **kwargs)

    def v2_get_category_info(self, shop_cipher=None):
        params = {}
        if shop_cipher:
            params.update({'shop_cipher': shop_cipher, 'locale': 'en-US'})

        prepared_request = self.build_request('product_category', **{
            'params': params
        })
        raw_data, tts_data = self.process_response('product_category', self.request(**prepared_request))
        return raw_data, tts_data


    def get_brand_info(self, *args, **kwargs):
        return getattr(self, '%s_get_brand_info' % self.api_version)(*args, **kwargs)

    def v2_get_brand_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id, 'keyword': ''})

        prepared_request = self.build_request('product_category', **{
            'params': params
        })
        raw_data, tp_data = self.process_response('product_category', self.request(**prepared_request))
        return raw_data, tp_data

    def get_attributes_info(self, *args, **kwargs):
        return getattr(self, '%s_get_attributes_info' % self.api_version)(*args, **kwargs)

    def v2_get_attributes_info(self, shop_id=None, category_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id, 'keyword': ''})
        if category_id:
            params.update({'cat_id': category_id})

        prepared_request = self.build_request('get_attributes', **{
            'params': params
        })
        response = self.request(**prepared_request)
        tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
        if tp_limit_rate_reset > 0:
            # self._logger.info(
            #     "Attributes: Too many requests, TiktokShop asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        no_validate = response.status_code == 429
        raw_attribute_data = self.process_response('default', response, no_validate=no_validate, no_sanitize=True)
        return raw_attribute_data
