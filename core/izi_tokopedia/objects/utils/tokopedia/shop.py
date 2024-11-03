# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import logging
from .api import TokopediaAPI
_logger = logging.getLogger(__name__)


class TokopediaShop(TokopediaAPI):

    def get_shop_info(self, shop_id=None):
        params = {}
        if shop_id:
            params.update({'shop_id': shop_id})

        prepared_request = self.build_request('shop_info', **{
            'params': params
        })
        # _logger.info('Prepare Request: %s' % prepared_request)
        return self.process_response('shop_info', self.request(**prepared_request))
