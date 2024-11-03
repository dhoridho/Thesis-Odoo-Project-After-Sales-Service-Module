# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

# from .api import TokopediaAPI
import requests
from base64 import b64encode
from datetime import datetime
from .tools import validate_response
from .endpoint import TokopediaEndpoint
import hashlib


# class TokopediaImages(TokopediaAPI):
class TokopediaImages(object):

    def __init__(self, client_id, client_secret, api_version="v3", **kwargs):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = kwargs.get('access_token', None)
        self.expired_date = kwargs.get('expired_date', None)
        self.token_type = kwargs.get('token_type', None)
        self.api_version = api_version
        self.endpoints = TokopediaEndpoint(self, host="image", api_version=api_version)

    def set_product_images(self, *args, **kwargs):
        return getattr(self, '%s_set_product_images' % self.api_version)(*args, **kwargs)

    def v3_set_product_images(self, shop_id=None, filename=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        if not filename:
            filename = False
            # self._logger.info("Product image not found.")

        prepared_request = self.build_request('upload_images', data={}, headers={}, files=filename, params=params, force_params=True)

        response = self.request(**prepared_request)
        res_product_image = self.process_response('upload_images', response, no_sanitize=True)
        return res_product_image

    def get_auth(self, token=False):
        if token:
            auth = 'Basic %s' % b64encode('{}:{}'.format(self.client_id, self.client_secret).encode()).decode()
        else:
            auth = '%s %s' % (self.token_type, self.access_token)
        return auth


    def upload_image(self, filename=None):
        headers = {
            'Authorization': self.get_auth(token=True),
        }
        params = {}
        # date_today = datetime.now().strftime("%Y/%m/%d")
        prepared_request = self.endpoints.build_request('upload_images', **{
            'headers': headers,
            'files': filename,
            'params': params,
            'force_params': True
        })
        response = validate_response(requests.request(**prepared_request, allow_redirects=False))
        return response.json()
