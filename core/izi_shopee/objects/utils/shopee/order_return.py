# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from .api import ShopeeAPI


class ShopeeReturn(ShopeeAPI):

    def __init__(self, sp_account, **kwargs):
        super(ShopeeReturn, self).__init__(sp_account, **kwargs)
        self.return_data = []
        self.return_data_raw = []

    def get_return_detail(self, **kwargs):
        return getattr(self, '%s_get_return_detail' % self.api_version)(**kwargs)

    def v2_get_return_detail(self, **kwargs):
        return_list = kwargs.get('return_list')
        for index, return_data in enumerate(return_list):
            # self._logger.info("Order: Get return detail %d of %d." % (index+1, len(return_list)))
            params = {
                'return_sn': return_data.get('return_sn')
            }
            prepared_request = self.build_request('return_detail',
                                                  self.sp_account.partner_id,
                                                  self.sp_account.partner_key,
                                                  self.sp_account.shop_id,
                                                  self.sp_account.host,
                                                  self.sp_account.access_token,
                                                  ** {
                                                      'params': params
                                                  })
            response_data = self.process_response('return_detail', self.request(**prepared_request))
            return_data.update(response_data)
        return return_list

    def get_return_list(self, **kwargs):
        return getattr(self, '%s_get_return_list' % self.api_version)(**kwargs)

    def v2_get_return_list(self, from_date, to_date, limit=0, per_page=50, **kwargs):
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        return_list = []
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])
            params = {
                'create_time_from': from_timestamp,
                'create_time_to': to_timestamp,
            }
            unlimited = not limit
            if unlimited:
                page_no = 0
                while unlimited:
                    params.update({
                        'page_size': per_page,
                        'page_no': page_no
                    })
                    prepared_request = self.build_request('return_list',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.host,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'params': params
                                                          })
                    response_data = self.process_response('return_list', self.request(**prepared_request))
                    if response_data:
                        if 'return' in response_data and response_data['return']:
                            return_list.extend(response_data['return'])
                            # self._logger.info("Order: Get order return list %d of unlimited." %
                            #                   len(response_data['return']))
                            if not response_data['more']:
                                unlimited = False
                            else:
                                page_no += per_page
                        else:
                            unlimited = False
                    else:
                        unlimited = False

        # self._logger.info("Order: Finished Get order return list %d record(s) imported." % len(return_list))
        return return_list
