# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime

from .api import ShopeeAPI


class ShopeeOrderWallet(ShopeeAPI):
    def __init__(self, sp_account, **kwargs):
        super(ShopeeOrderWallet, self).__init__(sp_account, **kwargs)

    def get_wallet_transaction_list(self, *args, **kwargs):
        return getattr(self, '%s_get_wallet_transaction_list' % self.api_version)(*args, **kwargs)

    def v2_get_wallet_transaction_list(self, from_date, to_date, limit=0, per_page=50):
        response_datas = []
        params = {}
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        if not date_ranges:
            date_ranges.append((from_date, to_date))
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])

            params.update({
                'create_time_from': from_timestamp,
                'create_time_to': to_timestamp
            })

            if limit > 0 and limit == len(response_datas):
                break

            unlimited = not limit
            if unlimited:
                page = 1
                while unlimited:
                    params.update({
                        'page_no': page,
                        'page_size': per_page
                    })
                    prepared_request = self.build_request('wallet_transaction_list',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.host,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'params': params
                                                          })
                    response_data = self.process_response('wallet_transaction_list', self.request(**prepared_request))
                    if response_data:
                        if 'transaction_list' in response_data and response_data['transaction_list']:
                            response_datas.extend(response_data['transaction_list'])
                            # self._logger.info("Order Wallets: Imported %d record(s) of unlimited." % len(response_datas))

                        if response_data['more']:
                            page += 1
                        else:
                            unlimited = False
                    else:
                        unlimited = False
            else:
                pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
                for pagination_page in pagination_pages:
                    params.update({
                        'page_no': pagination_page[0],
                        'page_size': pagination_page[1]
                    })
                    prepared_request = self.build_request('wallet_transaction_list',
                                                          self.sp_account.partner_id,
                                                          self.sp_account.partner_key,
                                                          self.sp_account.shop_id,
                                                          self.sp_account.host,
                                                          self.sp_account.access_token,
                                                          ** {
                                                              'params': params
                                                          })
                    response_data = self.process_response('wallet_transaction_list', self.request(**prepared_request))
                    if response_data:
                        if 'transaction_list' in response_data and response_data['transaction_list']:
                            response_datas.extend(response_data['transaction_list'])
                            # if limit == 1:
                                # self._logger.info("Order Wallets: Imported 1 record.")
                            # else:
                                # self._logger.info("Order Wallets: Imported %d record(s) of %d." %
                                #                   (len(response_datas), limit))

        # self._logger.info("Order Wallets: Finished %d record(s) imported." % len(response_datas))
        return response_datas
