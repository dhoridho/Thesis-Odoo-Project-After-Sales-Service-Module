# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import requests

from .api import TiktokAPI


class TiktokShop(TiktokAPI):
    def __init__(self, tts_account, **kwargs):
        super(TiktokShop, self).__init__(tts_account, **kwargs)

    def auth_shop(self):
        response_data = []
        prepared_request = self.build_request('auth_shop',)
        response = self.process_response('auth_shop', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if raw_data['code'] != 0:
                return response.json()
            else:
                response_data = raw_data['data']['shops']
        else:
            return response.json()

        return response_data
