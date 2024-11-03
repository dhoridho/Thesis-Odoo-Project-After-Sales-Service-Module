# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import time

from odoo.addons.izi_lazada.objects.utils.lazada.api import LazadaAPI


class LazadaDatamoat(LazadaAPI):

    def __init__(self, lz_account, **kwargs):
        super(LazadaDatamoat, self).__init__(lz_account, **kwargs)
        self.user_login = kwargs.get('user_login')
        self.user_ip = kwargs.get('user_ip')
        self.ati = kwargs.get('ati')

    def login(self, login_result, login_msg):
        params = {
            'time': str(int(time.time())),
            'appName': self.lz_account.app_name,
            'userId': self.user_login,
            'tid': self.lz_account.tid,
            'userIp': self.user_ip,
            'ati': self.ati,
            'loginResult': login_result,
            'loginMessage': login_msg
        }
        lz_request = self.endpoints.build_lz_request('datamoat_login', params=params)
        lz_response = self.lz_account.lz_client.execute(lz_request)
        return lz_response

    def compute_risk(self):
        params = {
            'time': str(int(time.time())),
            'appName': self.lz_account.app_name,
            'userId': self.user_login,
            'userIp': self.user_ip,
            'ati': self.ati,
        }
        lz_request = self.endpoints.build_lz_request('datamoat_compute_risk', params=params)
        lz_response = self.lz_account.lz_client.execute(lz_request)
        return lz_response
