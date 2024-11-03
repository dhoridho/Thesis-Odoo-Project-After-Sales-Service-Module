# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import requests

from .api import TiktokAPI


class TiktokLogistic(TiktokAPI):
    def __init__(self, tts_account, **kwargs):
        super(TiktokLogistic, self).__init__(tts_account, **kwargs)

    def get_warehouse_list(self):
        response_data = []
        prepared_request = self.build_request('get_warehouse_list',)
        response = self.process_response('get_warehouse_list', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if raw_data['code'] != 0:
                return response.json()
            else:
                response_data = raw_data['data']
        else:
            return response.json()

        return response_data

    def get_logistic_info(self, delivery_option_id=None):
        response_data = []
        params = {}
        if delivery_option_id:
            params.update({'delivery_option_id': delivery_option_id})

        prepared_request = self.build_request('get_logistic_info',)
        response = self.process_response('get_logistic_info', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if raw_data['code'] != 0:
                return response.json()
            else:
                response_data = raw_data['data']
        else:
            return response.json()

        return response_data
