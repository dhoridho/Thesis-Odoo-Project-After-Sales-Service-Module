# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import requests

from .api import LazadaAPI


class LazadaSeller(LazadaAPI):

    def get_seller_info(self):
        lz_request = self.endpoints.build_lz_request('seller_info')
        lz_client = self.lz_account.lz_client
        lz_seller_raw = self.process_response(
            'seller_info', lz_client.execute(lz_request, self.lz_account.access_token))
        return lz_seller_raw
