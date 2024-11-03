# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from .api import LazadaAPI


class LazadaLogistic(LazadaAPI):

    def get_shipping_info(self):
        lz_request = self.endpoints.build_lz_request('shipping_info')
        lz_client = self.lz_account.lz_client
        lz_logistic_raw = self.process_response(
            'shipping_info', lz_client.execute(lz_request, self.lz_account.access_token))
        return lz_logistic_raw
