# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from itertools import count
from .api import LazadaAPI


class LazadaFinance(LazadaAPI):

    def __init__(self, lz_account, **kwargs):
        super(LazadaFinance, self).__init__(lz_account, **kwargs)
        self.payout_data = []

    def get_transaction_detail(self, from_date, to_date, limit=0, per_page=100, time_mode=None, **kwargs):
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        lz_transaction_data = []
        for date_range in date_ranges:
            date_after = date_range[0].astimezone(self.lz_account.api_tz)
            date_before = date_range[1].astimezone(self.lz_account.api_tz)
            params = {
                'start_time': date_after.strftime("%Y-%m-%d"),
                'end_time': date_before.strftime("%Y-%m-%d"),
            }
            unlimited = not limit
            if unlimited:
                offset = 0
                while unlimited:
                    params.update({
                        'offset': offset,
                        'limit': per_page,
                    })
                    lz_request = self.endpoints.build_lz_request(
                        'transaction_details', **{'force_params': True, 'params': params})
                    lz_client = self.lz_account.lz_client
                    lz_transactions_raw = self.process_response(
                        'transaction_details', lz_client.execute(lz_request, self.lz_account.access_token))
                    if lz_transactions_raw:
                        lz_transaction_data.extend(lz_transactions_raw)
                        if len(lz_transactions_raw) < 100:
                            unlimited = False
                        else:
                            offset = offset + len(lz_transactions_raw)
                    else:
                        unlimited = False

        return lz_transaction_data
