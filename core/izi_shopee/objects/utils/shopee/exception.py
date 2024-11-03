# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
import json

_logger = logging.getLogger(__name__)


class ShopeeAPIError(Exception):

    def __init__(self, sp_header):
        if sp_header.get('message'):
            self.message = "Shopee API error with the code {error}: {message}"
        else:
            self.message = "Shopee API error with the code {error} and request ID: {request_id}"

        if sp_header.get('response') != '':
            self.message + ' caused by {response}'
        # _logger.error(json.dumps(sp_header, indent=1))
        super(ShopeeAPIError, self).__init__(self.message.format(**sp_header))
