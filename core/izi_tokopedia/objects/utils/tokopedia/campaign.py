# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime
import time
from .api import TokopediaAPI


class TokopediaCampaign(TokopediaAPI):
    def __init__(self, tp_account, **kwargs):
        super(TokopediaCampaign, self).__init__(tp_account, **kwargs)

    # Slash Price

    def get_slash_price(self, **kwargs):
        return getattr(self, '%s_get_slash_price' % self.api_version)(**kwargs)

    def v2_get_slash_price(self, shop_id=None, limit=0, per_page=20, **kwargs):
        response_datas = []
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        unlimited = not limit
        if unlimited:
            page = 1
            while unlimited:
                params.update({
                    'page': page,
                    'per_page': per_page
                })
                prepared_request = self.build_request('get_slash_price', params=params)
                response = self.request(**prepared_request)
                response_data = self.process_response('default', response)
                if response_data:
                    response_datas.extend(response_data)
                    # self._logger.info("Campaign/Slash Price: Imported %d record(s) of unlimited." % len(response_datas))
                    page += 1
                    time.sleep(1)
                else:
                    unlimited = False

        # self._logger.info("Campaign/Slash Price: Finished %d record(s) imported." % len(response_datas))
        return response_datas

    def add_slash_price(self, **kwargs):
        return getattr(self, '%s_add_slash_price' % self.api_version)(**kwargs)

    def v1_add_slash_price(self, shop_id=None, data=[]):
        prepared_request = self.build_request('add_slash_price',  json=data, params={'shop_id': int(shop_id)}, force_params=True)
        response = self.request(**prepared_request)
        response_data = self.process_response('default', response)
        return response_data

    def update_slash_price(self, **kwargs):
        return getattr(self, '%s_update_slash_price' % self.api_version)(**kwargs)

    def v1_update_slash_price(self, **kwargs):
        pass

    def cancel_slash_price(self, **kwargs):
        return getattr(self, '%s_update_slash_price' % self.api_version)(**kwargs)

    def v1_cancel_slash_price(self, **kwargs):
        pass

    # Bundle

    def get_bundle_list(self, **kwargs):
        return getattr(self, '%s_get_bundle_list' % self.api_version)(**kwargs)

    def v1_get_bundle_list(self, **kwargs):
        pass

    def get_bundle_info(self, **kwargs):
        return getattr(self, '%s_get_bundle_info' % self.api_version)(**kwargs)

    def v1_get_bundle_info(self, **kwargs):
        pass

    def add_bundle(self, **kwargs):
        return getattr(self, '%s_add_bundle' % self.api_version)(**kwargs)

    def v1_add_bundle(self, **kwargs):
        pass

    def cancel_bundle(self, **kwargs):
        return getattr(self, '%s_cancel_bundle' % self.api_version)(**kwargs)

    def v1_cancel_bundle(self, **kwargs):
        pass
