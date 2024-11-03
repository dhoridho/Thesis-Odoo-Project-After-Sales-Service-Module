# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from .api import ShopeeAPI


class ShopeePromotion(ShopeeAPI):
    def __init__(self, sp_account, **kwargs):
        super(ShopeePromotion, self).__init__(sp_account, **kwargs)

    # Product Discount
    def get_discount_list(self, **kwargs):
        return getattr(self, '%s_get_discount_list' % self.api_version)(**kwargs)

    def v2_get_discount_list(self, per_page=100, unlimited=True, status=[]):
        discount_list_data = []
        for discount_status in status:
            params = {
                'discount_status': discount_status,
                'page_size': per_page,
            }
            unlimited = True
            while unlimited:
                page = 1
                params.update({
                    'page_no': page
                })
                prepared_request = self.build_request('get_discount_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.host,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                response = self.process_response('get_discount_list', self.request(**
                                                 prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if 'discount_list' in raw_data['response'] and raw_data['response'].get('discount_list'):
                        discount_list_data.extend(raw_data['response'].get('discount_list'))
                        # self._logger.info("Promotion: Get Discount list %d of unlimited." %
                        #                   len(raw_data['response'].get('discount_list')))
                    if raw_data['response'].get('more'):
                        page += 1
                    else:
                        unlimited = False
                else:
                    # return False
                    unlimited = False
                    return response.json()
        # self._logger.info("Promotion: Finished Get discount List %d record(s) imported." % len(discount_list_data))
        return discount_list_data

    def get_discount(self, **kwargs):
        return getattr(self, '%s_get_discount' % self.api_version)(**kwargs)

    def v2_get_discount(self, per_page=50, unlimited=True, **kwargs):
        discount_data = []
        while unlimited:
            page = 1
            params = {
                'discount_id': int(kwargs.get('discount_id')),
                'page_no': page,
                'page_size': per_page,
            }
            prepared_request = self.build_request('get_discount',
                                                  self.sp_account.partner_id,
                                                  self.sp_account.partner_key,
                                                  self.sp_account.shop_id,
                                                  self.sp_account.host,
                                                  self.sp_account.access_token,
                                                  ** {
                                                      'params': params
                                                  })
            response = self.process_response('get_discount', self.request(**prepared_request), no_sanitize=True)
            if response.status_code == 200:
                raw_data = response.json()
                if page == 1:
                    discount_data = raw_data['response']
                else:
                    if 'item_list' in discount_data:
                        discount_data['item_list'].extend(raw_data['response'].get('item_list'))

                if raw_data['response'].get('more'):
                    page += 1
                else:
                    unlimited = False
            else:
                return False

            return discount_data

    def add_discount(self, **kwargs):
        return getattr(self, '%s_add_discount' % self.api_version)(**kwargs)

    def v2_add_discount(self, **kwargs):
        payload = {
            'discount_name': kwargs.get('promotion_name'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
        }
        prepared_request = self.build_request('add_discount',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_discount', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def add_discount_item(self, **kwargs):
        return getattr(self, '%s_add_discount_item' % self.api_version)(**kwargs)

    def v2_add_discount_item(self, **kwargs):
        payload = {
            'discount_id': int(kwargs.get('discount_id')),
            'item_list': kwargs.get('item_list'),
        }
        prepared_request = self.build_request('add_discount_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_discount_item', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def update_discount(self, **kwargs):
        return getattr(self, '%s_update_discount' % self.api_version)(**kwargs)

    def v2_update_discount(self, **kwargs):
        payload = {
            'discount_id': int(kwargs.get('promotion_id')),
            'discount_name': kwargs.get('promotion_name'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
        }
        prepared_request = self.build_request('update_discount',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('update_discount', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def delete_discount_item(self, **kwargs):
        return getattr(self, '%s_delete_discount_item' % self.api_version)(**kwargs)

    def v2_delete_discount_item(self, **kwargs):
        payload = {
            'discount_id': int(kwargs.get('discount_id')),
            'item_id': kwargs.get('item_id'),
            'model_id': kwargs.get('model_id', 0),
        }
        prepared_request = self.build_request('delete_discount_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_discount_item', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def delete_discount(self, **kwargs):
        return getattr(self, '%s_delete_discount' % self.api_version)(**kwargs)

    def v2_delete_discount(self, **kwargs):
        payload = {
            'discount_id': int(kwargs.get('promotion_id')),
        }
        prepared_request = self.build_request('delete_discount',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_discount', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def end_discount(self, **kwargs):
        return getattr(self, '%s_end_discount' % self.api_version)(**kwargs)

    def v2_end_discount(self, **kwargs):
        payload = {
            'discount_id': int(kwargs.get('promotion_id')),
        }
        prepared_request = self.build_request('end_discount',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('end_discount', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    # Voucher

    def get_voucher_list(self, **kwargs):
        return getattr(self, '%s_get_voucher_list' % self.api_version)(**kwargs)

    def v2_get_voucher_list(self, per_page=100, unlimited=True, status=[]):
        voucher_list_data = []
        for voucher_status in status:
            params = {
                'status': voucher_status,
                'page_size': per_page,
            }
            unlimited = True
            while unlimited:
                page = 1
                params.update({
                    'page_no': page
                })
                prepared_request = self.build_request('get_voucher_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.host,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                response = self.process_response('get_voucher_list', self.request(**prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if 'voucher_list' in raw_data['response'] and raw_data['response'].get('voucher_list'):
                        raw_voucher_data = [
                            dict(sp_voucher,
                                 **dict([('status', voucher_status)]))
                            for sp_voucher in raw_data['response'].get('voucher_list')
                        ]
                        voucher_list_data.extend(raw_voucher_data)
                    # self._logger.info("Promotion: Get Vocuher list %d of unlimited." %
                    #                   len(raw_data['response'].get('voucher_list')))
                    if raw_data['response'].get('more'):
                        page += 1
                    else:
                        unlimited = False
                else:
                    # return False
                    unlimited = False
                    return response.json()
        # self._logger.info("Promotion: Finished Get voucher List %d record(s) imported." % len(voucher_list_data))
        return voucher_list_data

    def get_voucher(self, **kwargs):
        return getattr(self, '%s_get_voucher' % self.api_version)(**kwargs)

    def v2_get_voucher(self, **kwargs):
        vocuher_data = {}
        params = {
            'voucher_id': kwargs.get('voucher_id'),
        }
        prepared_request = self.build_request('get_voucher',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_voucher', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            raw_data['response']['status'] = kwargs.get('status', False)
            vocuher_data = raw_data['response']

        return vocuher_data

    def add_voucher(self, **kwargs):
        return getattr(self, '%s_add_voucher' % self.api_version)(**kwargs)

    def v2_add_voucher(self, **kwargs):
        payload = {
            'voucher_name': kwargs.get('promotion_name'),
            'voucher_code': kwargs.get('voucher_code'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
            'voucher_type': kwargs.get('voucher_type'),
            'reward_type': kwargs.get('reward_type'),
            'usage_quantity': kwargs.get('usage_quantity'),
            'min_basket_price': kwargs.get('min_basket_price'),
            'display_channel_list': kwargs.get('display_channel_list'),
        }
        if kwargs.get('reward_type') == 1:
            payload.update({
                'discount_amount': kwargs.get('discount_amount')
            })
        else:
            payload.update({
                'percentage': kwargs.get('percentage'),
                'max_price': kwargs.get('max_price'),
            })

        if kwargs.get('voucher_type') == 2:
            payload.update({
                'item_id_list': kwargs.get('item_id_list'),
            })

        prepared_request = self.build_request('add_voucher',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_voucher', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def update_voucher(self, **kwargs):
        return getattr(self, '%s_update_voucher' % self.api_version)(**kwargs)

    def v2_update_voucher(self, **kwargs):
        payload = {
            'voucher_id': kwargs.get('promotion_id'),
            'voucher_name': kwargs.get('promotion_name'),
            'voucher_code': kwargs.get('voucher_code'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
            'voucher_type': kwargs.get('voucher_type'),
            'reward_type': kwargs.get('reward_type'),
            'usage_quantity': kwargs.get('usage_quantity'),
            'min_basket_price': kwargs.get('min_basket_price'),
            'display_channel_list': kwargs.get('display_channel_list'),
        }
        if kwargs.get('reward_type') == 1:
            payload.update({
                'discount_amount': kwargs.get('discount_amount')
            })
        else:
            payload.update({
                'percentage': kwargs.get('percentage'),
                'max_price': kwargs.get('max_price'),

            })

        if kwargs.get('voucher_type') == 2:
            payload.update({
                'item_id_list': kwargs.get('item_id_list'),
            })

        prepared_request = self.build_request('update_voucher',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('update_voucher', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def delete_voucher(self, **kwargs):
        return getattr(self, '%s_delete_voucher' % self.api_version)(**kwargs)

    def v2_delete_voucher(self, **kwargs):
        payload = {
            'voucher_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('delete_voucher',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_voucher', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def end_voucher(self, **kwargs):
        return getattr(self, '%s_end_voucher' % self.api_version)(**kwargs)

    def v2_end_voucher(self, **kwargs):
        payload = {
            'voucher_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('end_voucher',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('end_voucher', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    # Bundle deal

    def get_bundle_list(self, **kwargs):
        return getattr(self, '%s_get_bundle_list' % self.api_version)(**kwargs)

    def v2_get_bundle_list(self, per_page=100, unlimited=True, status=[]):
        bundle_list_data = []
        for bundle_status in status:
            if bundle_status == 2:
                bundle_status_str = 'upcoming'
            elif bundle_status == 3:
                bundle_status_str = 'ongoing'
            elif bundle_status == 4:
                bundle_status_str = 'expired'

            params = {
                'time_status': bundle_status,
                'page_size': per_page,
            }
            unlimited = True
            while unlimited:
                page = 1
                params.update({
                    'page_no': page
                })
                prepared_request = self.build_request('get_bundle_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.host,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                response = self.process_response('get_bundle_list', self.request(**prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if 'bundle_deal_list' in raw_data and raw_data['response'].get('bundle_deal_list'):
                        raw_bundle_data = [
                            dict(sp_bundle,
                                 **dict([('status', bundle_status_str)]))
                            for sp_bundle in raw_data['response'].get('bundle_deal_list')
                        ]
                        bundle_list_data.extend(raw_bundle_data)
                    # self._logger.info("Promotion: Get Bundle list %d of unlimited." %
                    #                   len(raw_data['response'].get('bundle_deal_list')))
                    if raw_data['response'].get('more'):
                        page += 1
                    else:
                        unlimited = False
                else:
                    # return False
                    unlimited = False
                    return response.json()
        # self._logger.info("Promotion: Finished Get bundle List %d record(s) imported." % len(bundle_list_data))
        return bundle_list_data

    def get_bundle(self, **kwargs):
        return getattr(self, '%s_get_bundle' % self.api_version)(**kwargs)

    def v2_get_bundle(self, **kwargs):
        bundle_data = {}
        params = {
            'bundle_deal_id': kwargs.get('bundle_deal_id'),
        }
        prepared_request = self.build_request('get_bundle',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_bundle', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            raw_data['response']['status'] = kwargs.get('status', False)
            bundle_data = raw_data['response']

        return bundle_data

    def get_bundle_item(self, **kwargs):
        return getattr(self, '%s_get_bundle_item' % self.api_version)(**kwargs)

    def v2_get_bundle_item(self, **kwargs):
        bundle_item_data = []
        params = {
            'bundle_deal_id': kwargs.get('bundle_deal_id'),
        }
        prepared_request = self.build_request('get_bundle_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_bundle_item', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            bundle_item_data.extend(raw_data['response']['item_list'])

        return bundle_item_data

    def add_bundle(self, **kwargs):
        return getattr(self, '%s_add_bundle' % self.api_version)(**kwargs)

    def v2_add_bundle(self, **kwargs):
        payload = {
            'name': kwargs.get('promotion_name'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
            'rule_type': kwargs.get('rule_type'),
            'min_amount': kwargs.get('min_amount'),
            'purchase_limit': kwargs.get('purchase_limit')
        }
        if kwargs.get('rule_type') == 1:
            payload.update({
                'fix_price': kwargs.get('fix_price')
            })
        elif kwargs.get('rule_type') == 2:
            payload.update({
                'discount_percentage': kwargs.get('discount_percentage')
            })
        elif kwargs.get('rule_type') == 3:
            payload.update({
                'discount_value': kwargs.get('discount_value')
            })
        prepared_request = self.build_request('add_bundle',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_bundle', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def add_bundle_item(self, **kwargs):
        return getattr(self, '%s_add_bundle_item' % self.api_version)(**kwargs)

    def v2_add_bundle_item(self, **kwargs):
        payload = {
            'bundle_deal_id': kwargs.get('bundle_deal_id'),
            'item_list': kwargs.get('item_list'),
        }
        prepared_request = self.build_request('add_bundle_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_bundle_item', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return raw_data
            else:
                return raw_data['response']
        else:
            return response.json()

    def update_bundle(self, **kwargs):
        return getattr(self, '%s_update_bundle' % self.api_version)(**kwargs)

    def v2_update_bundle(self, **kwargs):
        payload = {
            'bundle_deal_id': kwargs.get('promotion_id'),
            'name': kwargs.get('promotion_name'),
        }
        payload.update(**kwargs)
        prepared_request = self.build_request('update_bundle',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('update_bundle', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def delete_bundle_item(self, **kwargs):
        return getattr(self, '%s_delete_bundle_item' % self.api_version)(**kwargs)

    def v2_delete_bundle_item(self, **kwargs):
        payload = {
            'bundle_deal_id': kwargs.get('bundle_deal_id'),
            'item_list': kwargs.get('item_list'),
        }
        prepared_request = self.build_request('delete_bundle_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_bundle_item', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def end_bundle(self, **kwargs):
        return getattr(self, '%s_end_bundle' % self.api_version)(**kwargs)

    def v2_end_bundle(self, **kwargs):
        payload = {
            'bundle_deal_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('end_bundle',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('end_bundle', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def delete_bundle(self, **kwargs):
        return getattr(self, '%s_delete_bundle' % self.api_version)(**kwargs)

    def v2_delete_bundle(self, **kwargs):
        payload = {
            'bundle_deal_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('delete_bundle',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_bundle', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    # Add On Deal

    def get_addon_deal_list(self, **kwargs):
        return getattr(self, '%s_get_addon_deal_list' % self.api_version)(**kwargs)

    def v2_get_addon_deal_list(self, per_page=100, unlimited=True, status=[]):
        addon_list_data = []
        for addon_status in status:
            params = {
                'promotion_status': addon_status,
                'page_size': per_page,
            }
            unlimited = True
            while unlimited:
                page = 1
                params.update({
                    'page_no': page
                })
                prepared_request = self.build_request('get_add_on_deal_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.host,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                response = self.process_response('get_add_on_deal_list', self.request(**
                                                 prepared_request), no_sanitize=True)
                if response.status_code == 200:
                    raw_data = response.json()
                    if 'add_on_deal_list' in raw_data and raw_data['response'].get('add_on_deal_list'):
                        raw_addon_data = [
                            dict(sp_bundle,
                                 **dict([('status', addon_status)]))
                            for sp_bundle in raw_data['response'].get('add_on_deal_list')
                        ]
                        addon_list_data.extend(raw_addon_data)
                    # self._logger.info("Promotion: Get Addon Deal list %d of unlimited." %
                    #                   len(raw_data['response'].get('add_on_deal_list')))
                    if raw_data['response'].get('more'):
                        page += 1
                    else:
                        unlimited = False
                else:
                    # return False
                    unlimited = False
                    return response.json()

        # self._logger.info("Promotion: Finished Get Addon Deal List %d record(s) imported." % len(addon_list_data))
        return addon_list_data

    def get_addon_deal(self, **kwargs):
        return getattr(self, '%s_get_addon_deal' % self.api_version)(**kwargs)

    def v2_get_addon_deal(self, **kwargs):
        addon_data = {}
        params = {
            'add_on_deal_id': kwargs.get('addon_deal_id'),
        }
        prepared_request = self.build_request('get_add_on_deal',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_add_on_deal', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            raw_data['response']['status'] = kwargs.get('status', False)
            addon_data = raw_data['response']

        return addon_data

    def get_addon_main_item(self, **kwargs):
        return getattr(self, '%s_get_addon_main_item' % self.api_version)(**kwargs)

    def v2_get_addon_main_item(self, **kwargs):
        addon_main_item_data = []
        params = {
            'add_on_deal_id': kwargs.get('addon_deal_id'),
        }
        prepared_request = self.build_request('get_add_on_deal_main_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_add_on_deal_main_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            addon_main_item_data.extend(raw_data['response']['main_item_list'])

        return addon_main_item_data

    def get_addon_sub_item(self, **kwargs):
        return getattr(self, '%s_get_addon_sub_item' % self.api_version)(**kwargs)

    def v2_get_addon_sub_item(self, **kwargs):
        addon_sub_item_data = []
        params = {
            'add_on_deal_id': kwargs.get('addon_deal_id'),
        }
        prepared_request = self.build_request('get_add_on_deal_sub_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        response = self.process_response('get_add_on_deal_sub_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            addon_sub_item_data.extend(raw_data['response']['sub_item_list'])

        return addon_sub_item_data

    def add_addon(self, **kwargs):
        return getattr(self, '%s_add_addon' % self.api_version)(**kwargs)

    def v2_add_addon(self, **kwargs):
        payload = {
            'add_on_deal_name': kwargs.get('promotion_name'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
            'promotion_type': kwargs.get('promotion_type'),
        }
        if kwargs.get('purchase_min_spend', False):
            payload.update({
                'purchase_min_spend': kwargs.get('purchase_min_spend')
            })
        if kwargs.get('per_gift_num', False):
            payload.update({
                'per_gift_num': kwargs.get('per_gift_num')
            })
        if kwargs.get('promotion_purchase_limit', False):
            payload.update({
                'promotion_purchase_limit': kwargs.get('promotion_purchase_limit')
            })
        prepared_request = self.build_request('add_add_on_deal',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_add_on_deal', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def add_addon_main_item(self, **kwargs):
        return getattr(self, '%s_add_addon_main_item' % self.api_version)(**kwargs)

    def v2_add_addon_main_item(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('add_on_deal_id'),
            'main_item_list': kwargs.get('main_item_list'),
        }
        prepared_request = self.build_request('add_add_on_deal_main_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_add_on_deal_main_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def add_addon_sub_item(self, **kwargs):
        return getattr(self, '%s_add_addon_sub_item' % self.api_version)(**kwargs)

    def v2_add_addon_sub_item(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('add_on_deal_id'),
            'sub_item_list': kwargs.get('sub_item_list'),
        }
        prepared_request = self.build_request('add_add_on_deal_sub_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('add_add_on_deal_sub_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def update_addon(self, **kwargs):
        return getattr(self, '%s_update_addon' % self.api_version)(**kwargs)

    def v2_update_addon(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('promotion_id'),
            'add_on_deal_name': kwargs.get('promotion_name'),
            'start_time': kwargs.get('start_time'),
            'end_time': kwargs.get('end_time'),
        }
        if kwargs.get('purchase_min_spend', False):
            payload.update({
                'purchase_min_spend': kwargs.get('purchase_min_spend')
            })
        if kwargs.get('per_gift_num', False):
            payload.update({
                'per_gift_num': kwargs.get('per_gift_num')
            })
        if kwargs.get('promotion_purchase_limit', False):
            payload.update({
                'promotion_purchase_limit': kwargs.get('promotion_purchase_limit')
            })
        prepared_request = self.build_request('update_add_on_deal',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('update_add_on_deal', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return raw_data['response']
        else:
            return False

    def delete_addon(self, **kwargs):
        return getattr(self, '%s_delete_addon' % self.api_version)(**kwargs)

    def v2_delete_addon(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('delete_add_on_deal',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_add_on_deal', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def delete_addon_main_item(self, **kwargs):
        return getattr(self, '%s_delete_addon_main_item' % self.api_version)(**kwargs)

    def v2_delete_addon_main_item(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('add_on_deal_id'),
            'main_item_list': kwargs.get('main_item_list')
        }
        prepared_request = self.build_request('delete_add_on_deal_main_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_add_on_deal_main_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def delete_addon_sub_item(self, **kwargs):
        return getattr(self, '%s_delete_addon_main_item' % self.api_version)(**kwargs)

    def v2_delete_addon_sub_item(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('add_on_deal_id'),
            'sub_item_list': kwargs.get('sub_item_list')
        }
        prepared_request = self.build_request('delete_add_on_deal_sub_item',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('delete_add_on_deal_sub_item',
                                         self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False

    def end_addon(self, **kwargs):
        return getattr(self, '%s_end_addon' % self.api_version)(**kwargs)

    def v2_end_addon(self, **kwargs):
        payload = {
            'add_on_deal_id': kwargs.get('promotion_id'),
        }
        prepared_request = self.build_request('end_add_on_deal',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'json': payload
                                              })
        response = self.process_response('end_add_on_deal', self.request(**prepared_request), no_sanitize=True)
        if response.status_code == 200:
            raw_data = response.json()
            if 'error' in raw_data and raw_data['error']:
                return False
            else:
                return True
        else:
            return False
