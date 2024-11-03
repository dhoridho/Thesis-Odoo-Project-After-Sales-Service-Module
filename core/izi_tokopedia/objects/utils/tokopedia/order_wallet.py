# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime

from .api import TokopediaAPI


class TokopediaOrderWallet(TokopediaAPI):
    def __init__(self, tp_account, **kwargs):
        super(TokopediaOrderWallet, self).__init__(tp_account, **kwargs)

    def get_saldo_history(self, *args, **kwargs):
        return getattr(self, '%s_get_saldo_history' % self.api_version)(*args, **kwargs)

    def v1_get_saldo_history(self, from_date, to_date, shop_id=None, limit=0, per_page=500):
        response_datas = []
        self.endpoints.tp_account.shop_id = shop_id
        params = {}

        date_ranges = self.pagination_date_range(from_date, to_date)
        if not date_ranges:
            from_date = datetime(from_date.year, from_date.month, from_date.day)
            to_date = datetime(to_date.year, to_date.month, to_date.day)
            date_ranges.append((from_date, to_date))
        for date_range in date_ranges:
            from_timestamp = date_range[0]
            to_timestamp = date_range[1]

            params.update({
                'from_date': from_timestamp.strftime("%Y-%m-%d"),
                'to_date': to_timestamp.strftime("%Y-%m-%d")
            })

            if limit > 0 and limit == len(response_datas):
                break

            unlimited = not limit
            if unlimited:
                page = 1
                while unlimited:
                    params.update({
                        'page': page,
                        'per_page': per_page
                    })
                    prepared_request = self.build_request('saldo_history', params=params)
                    response = self.request(**prepared_request)
                    response_data = self.process_response('default', response)
                    if response_data['saldo_history']:
                        response_datas.extend(response_data['saldo_history'])
                        # self._logger.info("Order Wallets: Imported %d record(s) of unlimited." % len(response_datas))

                    if response_data['have_next_page']:
                        page += 1
                    else:
                        unlimited = False
            else:
                pagination_pages = self.pagination_get_pages(limit=limit, per_page=per_page)
                for pagination_page in pagination_pages:
                    params.update({
                        'page': pagination_page[0],
                        'per_page': pagination_page[1]
                    })
                    prepared_request = self.build_request('order_list', params=params)
                    response = self.request(**prepared_request)
                    response_data = self.process_response('order_list', response)
                    if response_data['saldo_history']:
                        response_datas.extend(response_data['saldo_history'])
                        # if limit == 1:
                        #     self._logger.info("Order Wallets: Imported 1 record.")
                        # else:
                        #     self._logger.info("Order Wallets: Imported %d record(s) of %d." % (len(response_datas), limit))

        # self._logger.info("Order Wallets: Finished %d record(s) imported." % len(response_datas))
        return response_datas
