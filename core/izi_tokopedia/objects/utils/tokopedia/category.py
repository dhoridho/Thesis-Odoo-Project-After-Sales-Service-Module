# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from .api import TokopediaAPI
import time

class TokopediaCategory(TokopediaAPI):

    def get_category_info(self, *args, **kwargs):
        return getattr(self, '%s_get_category_info' % self.api_version)(*args, **kwargs)

    def v1_get_category_info(self, shop_id=None):
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

    def v1_get_attributes_info(self, shop_id=None, category_id=None):
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
            #     "Attributes: Too many requests, Tokopedia asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        no_validate = response.status_code == 429
        raw_attribute_data = self.process_response('default', response, no_validate=no_validate, no_sanitize=True)
        return raw_attribute_data

    def get_variants_info(self, *args, **kwargs):
        return getattr(self, '%s_get_variants_info' % self.api_version)(*args, **kwargs)

    def v2_get_variants_info(self, shop_id=None, category_id=None):
        params = {}
        if shop_id:
            params.update({
                'shop_id': shop_id
            })

        if category_id:
            params.update({'cat_id': category_id})

        prepared_request = self.build_request('get_variants', **{
            'params': params
        })
        response = self.request(**prepared_request)
        tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
        if tp_limit_rate_reset > 0:
            # self._logger.info(
            #     "Variants: Too many requests, Tokopedia asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        no_validate = response.status_code == 429
        raw_variant_data = self.process_response('default', response, no_validate=no_validate, no_sanitize=True)
        return raw_variant_data