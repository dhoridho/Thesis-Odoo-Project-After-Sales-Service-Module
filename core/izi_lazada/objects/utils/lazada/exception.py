# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
import json

_logger = logging.getLogger(__name__)


class LazadaAPIError(Exception):

    def __init__(self, lz_header):
        self.message = "Lazada API error with the code {code}: {message}"
        if lz_header.get('message') != '':
            self.message + ' caused by {message}'
        _logger.error(json.dumps(lz_header, indent=1))
        super(LazadaAPIError, self).__init__(self.message.format(**lz_header))
