# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import ShopeeAPI


class ShopeeShop(ShopeeAPI):

    def get_profile_info(self, data):
        prepared_request = self.build_request('profile_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token)
        response = self.process_response('profile_info', self.request(**prepared_request), no_sanitize=True)
        # data.update(response)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                resp_data = raw_data['response']
                data.update(resp_data)
                return data
        else:
            return False
        # return data

    def get_shop_info(self):
        prepared_request = self.build_request('shop_info',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token)
        raw_data, sp_data_shop = self.process_response('shop_info', self.request(**prepared_request))
        if raw_data:
            raw_data.update({
                'shop_id': self.sp_account.shop_id
            })
            if sp_data_shop:
                # raw_data = self.get_profile_info(raw_data)
                profile_data = self.get_profile_info(raw_data)
            if profile_data:
                raw_data = profile_data
            else:
                raw_data.update({
                    'description': sp_data_shop.get('shop_description')
                })
        else:
            raw_data = {}
        return raw_data

    def get_shop_address(self):
        prepared_request = self.build_request('shop_address',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token)
        raw_data = self.process_response('shop_address', self.request(**prepared_request))
        raw_data.update({
            'shop_id': self.sp_account.shop_id
        })
        return raw_data
