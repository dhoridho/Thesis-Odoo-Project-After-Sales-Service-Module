# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
from .api import TiktokAPI
import time


class TiktokPromotion(TiktokAPI):
    def __init__(self, tts_account, **kwargs):
        super(TiktokPromotion, self).__init__(tts_account, **kwargs)

    # Product Discount
    def get_promotion_list(self, **kwargs):
        return getattr(self, '%s_get_promotion_list' % self.api_version)(**kwargs)

    def v2_get_promotion_list(self, per_page=50, unlimited=True, status=[], title=''):
        promotion_list_data = []
        for promotion_status in status:
            if title:
                params = {
                    'status': promotion_status,
                    'activity_title': title,
                    'page_size': per_page,
                }
            else:
                params = {
                    'status': promotion_status,
                    'page_size': per_page,
                }
            offset = 0
            unlimited = True
            page = ''
            while unlimited:
                params.update({
                    # 'offset': offset,
                    'page_token': page
                })
                prepared_request = self.build_request('get_promotion_list', **{
                                                          'json': params
                                                      })
                response = self.process_response('get_promotion_list', self.request(**
                                                                                   prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if raw_data['code'] != 0:
                        unlimited = False
                        return response.json()
                    if 'promotion_list' in raw_data['data'] and raw_data['data'].get('promotion_list'):
                        promotion_list_data.extend(raw_data['data'].get('promotion_list'))
                        # offset += len(raw_data['data'].get('promotion_list'))
                        # if offset >= raw_data['data'].get('total'):
                        #     unlimited = False
                        # else:
                        #     page += 1
                        next_page = raw_data['data'].get('next_page_token')
                        if not next_page or next_page != '':
                            unlimited = False
                        else:
                            page = raw_data['data'].get('next_page_token')
                    else:
                        unlimited = False
                else:
                    unlimited = False
                    return response.json()
        # self._logger.info("Promotion: Finished Get discount List %d record(s) imported." % len(discount_list_data))
        return promotion_list_data

    def get_promotion_detail(self, **kwargs):
        return getattr(self, '%s_get_promotion_detail' % self.api_version)(**kwargs)

    def v2_get_promotion_detail(self, **kwargs):
        promotion_data = []
        params = {
            'promotion_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('get_promotion_detail', **{
                                                'params': params
                                            })
        response = self.process_response('get_promotion_detail', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if raw_data['code'] != 0:
                promotion_data = raw_data['data']
            else:
                return response.json()
        else:
            return response.json()
        return promotion_data

    def get_coupon_list(self, **kwargs):
        return getattr(self, '%s_get_coupon_list' % self.api_version)(**kwargs)

    def v2_get_coupon_list(self, per_page=50, unlimited=True, status=[], title=''):
        coupon_list_data = []
        for coupon_status in status:
            if title:
                params = {
                    'status': coupon_status,
                    'activity_title': title,
                    'page_size': per_page,
                }
            else:
                params = {
                    'status': coupon_status,
                    'page_size': per_page,
                }
            offset = 0
            unlimited = True
            page = ''
            while unlimited:
                params.update({
                    # 'offset': offset,
                    'page_token': page
                })
                prepared_request = self.build_request('get_coupon_list', **{
                                                          'json': params
                                                      })
                response = self.process_response('get_coupon_list', self.request(**
                                                                                   prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if raw_data['code'] != 0:
                        unlimited = False
                        return response.json()
                    if 'promotion_list' in raw_data['data'] and raw_data['data'].get('promotion_list'):
                        coupon_list_data.extend(raw_data['data'].get('promotion_list'))
                        # offset += len(raw_data['data'].get('promotion_list'))
                        # if offset >= raw_data['data'].get('total'):
                        #     unlimited = False
                        # else:
                        #     page += 1
                        next_page = raw_data['data'].get('next_page_token')
                        if not next_page or next_page != '':
                            unlimited = False
                        else:
                            page = raw_data['data'].get('next_page_token')
                    else:
                        unlimited = False
                else:
                    unlimited = False
                    return response.json()
        # self._logger.info("Promotion: Finished Get discount List %d record(s) imported." % len(discount_list_data))
        return coupon_list_data

    def get_coupon_detail(self, **kwargs):
        return getattr(self, '%s_get_coupon_detail' % self.api_version)(**kwargs)

    def v2_get_coupon_detail(self, **kwargs):
        coupon_data = []
        params = {
            'coupon_id': kwargs.get('coupon_id'),
        }
        prepared_request = self.build_request('get_coupon_detail', **{
                                                'params': params
                                            })
        response = self.process_response('get_coupon_detail', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if raw_data['code'] != 0:
                coupon_data = raw_data['data']
            else:
                return response.json()
        else:
            return response.json()
        return coupon_data