# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
from datetime import datetime

from .api import TiktokAPI


class TiktokOrderWallet(TiktokAPI):
    def __init__(self, sp_account, **kwargs):
        super(TiktokOrderWallet, self).__init__(sp_account, **kwargs)

    def get_finance_settlements_list(self, *args, **kwargs):
        return getattr(self, '%s_get_finance_settlements_list' % self.api_version)(*args, **kwargs)

    def v2_get_finance_settlements_list(self, from_date, to_date, per_page=50):
        response_datas = []
        datas = {}
        date_ranges = self.pagination_datetime_range(from_date, to_date)
        if not date_ranges:
            date_ranges.append((from_date, to_date))
        for date_range in date_ranges:
            from_timestamp = self.to_api_timestamp(date_range[0])
            to_timestamp = self.to_api_timestamp(date_range[1])

            datas.update({
                'request_time_from': from_timestamp,
                'request_time_to': to_timestamp,
                'page_size': per_page,
                'sort_type': 1,
            })

            prepared_request = self.build_request('finance_settlements', ** {
                                                      'json': datas
                                                  })
            response_data = self.process_response('finance_settlements', self.request(**prepared_request), no_sanitize=True)
            if response_data.status_code == 200:
                raw_data = response_data.json()
                if raw_data['code'] != 0:
                    return response_data.json()
                if 'settlement_list' in raw_data['data'] and raw_data['data']['settlement_list']:
                    response_datas.extend(raw_data['data']['settlement_list'])
                    # self._logger.info("Order Wallets: Imported %d record(s) of unlimited." % len(response_datas))
            else:
                return response_data.json()

        # self._logger.info("Order Wallets: Finished %d record(s) imported." % len(response_datas))
        return response_datas
