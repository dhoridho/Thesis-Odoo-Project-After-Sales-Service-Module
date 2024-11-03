# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import time
from .api import TiktokAPI


class TiktokProduct(TiktokAPI):

    def __init__(self, tp_account, **kwargs):
        super(TiktokProduct, self).__init__(tp_account, **kwargs)

    def get_product_info(self, *args, **kwargs):
        return getattr(self, '%s_get_product_info' % self.api_version)(*args, **kwargs)

    def v1_get_product_info(self, shop_id=None, product_id=None, limit=0, per_page=50):
        product_data, product_data_raw = [], []
        params = {}

        if shop_id:
            params.update({
                'shop_id': shop_id
            })

        if product_id:
            limit = 1
            if isinstance(product_id, list):
                product_id = ','.join([str(pid) for pid in product_id])
            params.update({
                'product_id': product_id
            })

        unlimited = not limit
        if unlimited:
            page = 1
            max_retry = 0
            while unlimited:
                params.update({
                    'page': page,
                    'per_page': per_page
                })
                prepared_request = self.build_request('product_info', **{
                    'params': params
                })
                time.sleep(1)
                raw_data, tp_data = self.process_response('product_info', self.request(**prepared_request))
                if raw_data:
                    product_data.extend(tp_data)
                    product_data_raw.extend(raw_data)
                    # self._logger.info("Product: Imported %d record(s) of unlimited." % len(product_data))
                    page += 1
                else:
                    if max_retry <= 3:
                        max_retry += 1
                    else:
                        unlimited = False
        else:
            pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
            for pagination_page in pagination_pages:
                params.update({
                    'page': pagination_page[0],
                    'per_page': pagination_page[1]
                })
                prepared_request = self.build_request('product_info', **{
                    'params': params
                })
                raw_data, tp_data = self.process_response('product_info', self.request(**prepared_request))
                if raw_data:
                    product_data.extend(tp_data)
                    product_data_raw.extend(raw_data)
                    # if limit == 1:
                    #     self._logger.info("Product: Imported 1 record.")
                    # else:
                    #     self._logger.info("Product: Imported %d record(s) of %d." % (len(product_data), limit))

        # self._logger.info("Product: Finished %d record(s) imported." % len(product_data))
        return product_data_raw, product_data

    def create_new_product(self, *args, **kwargs):
        return getattr(self, '%s_create_new_product' % self.api_version)(*args, **kwargs)

    def v3_create_new_product(self, shop_id=None, products=None):
        params = {}
        if shop_id:
            params.update({
                'shop_id': shop_id
            })

        if products:
            data = {
                'products': products
            }
        prepared_request = self.build_request('create_product', json=data, params=params, force_params=True)

        response = self.request(**prepared_request)
        tp_limit_rate_reset = abs(float(response.headers.get('X-Ratelimit-Reset-After', 0)))
        if tp_limit_rate_reset > 0:
            # self._logger.info(
            #     "Create Products: Too many requests, Tiktok asking to waiting for %s second(s)" % str(tp_limit_rate_reset))
            time.sleep(tp_limit_rate_reset + 1)
        no_validate = response.status_code == 429
        raw_product_data = self.process_response('default', response, no_validate=no_validate, no_sanitize=True)
        return raw_product_data