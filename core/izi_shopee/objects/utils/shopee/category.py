# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from .api import ShopeeAPI


class ShopeeCategory(ShopeeAPI):

    def get_category_list(self):
        params = {}
        params.update({
            'language': 'en'
        })
        prepared_request = self.build_request('category_list',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              **{
                                                  'params': params
                                              })
        raw_data, sp_data = self.process_response('category_list', self.request(**prepared_request))
        # temp_raw_data = raw_data['category_list']
        # for index, data in enumerate(temp_raw_data):
        #     if data['parent_category_id'] != 0 and data['has_children'] != True:
        #         sp_brand_data = self.get_brand_list(data['category_id'])
        #         if sp_brand_data:
        #             raw_data['category_list'][index].update({
        #                 'has_brand': True, 'brand_list': sp_brand_data['brand_list']
        #             })
        #             sp_data[index].update({
        #                 'has_brand': True, 'brand_list': sp_brand_data['brand_list']
        #             })
        #         else:
        #             raw_data['category_list'][index].update({
        #                 'has_brand': False,
        #             })
        #             sp_data[index].update({
        #                 'has_brand': False,
        #             })
        #         sp_attribute_data = self.get_attribute_list(data['category_id'])
        #         if sp_attribute_data:
        #             raw_data['category_list'][index].update({
        #                 'has_attribute': True, 'attribute_list': sp_attribute_data['attribute_list']
        #             })
        #             sp_data[index].update({
        #                 'has_attribute': True, 'attribute_list': sp_attribute_data['attribute_list']
        #             })
        #         else:
        #             raw_data['category_list'][index].update({
        #                 'has_attribute': False,
        #             })
        #             sp_data[index].update({
        #                 'has_attribute': False,
        #             })
        #     else:
        #         raw_data['category_list'][index].update({
        #             'has_brand': False,
        #             'has_attribute': False,
        #         })
        #         sp_data[index].update({
        #             'has_brand': False,
        #             'has_attribute': False,
        #         })
        return raw_data, sp_data

    def get_brand_list(self, category_id, limit=0):
        params = {}
        unlimited = not limit
        if unlimited:
            offset = 0
            data_raw = []
            brand_id = False
            brand_list = []
            while unlimited:
                params.update({
                    'offset': offset,
                    'page_size': 50,
                    'category_id': category_id or 0,
                    'status': 1,            ### 1) Normal Brand 2) Pending Brand
                    'language': 'en'
                })
                prepared_request = self.build_request('brand_list',
                                                      self.sp_account.partner_id,
                                                      self.sp_account.partner_key,
                                                      self.sp_account.shop_id,
                                                      self.sp_account.host,
                                                      self.sp_account.access_token,
                                                      ** {
                                                          'params': params
                                                      })
                sp_data_list = self.process_response('brand_list', self.request(**prepared_request))
                if sp_data_list:
                    if not sp_data_list['has_next_page']:
                        unlimited = False
                    else:
                        for brand_data in sp_data_list['brand_list']:
                            if brand_id in brand_list:
                               unlimited = False
                            else:
                                brand_id = brand_data.get('brand_id')
                                brand_list.append(brand_data.get('brand_id'))

                        #
                        # # if data_raw == sp_data_list['brand_list']:
                        #     unlimited = False
                        # else:
                        #     data_raw = sp_data_list['brand_list']
                        offset += len(sp_data_list['brand_list'])
                else:
                    unlimited = False
            return sp_data_list

    def get_attribute_list(self, category_id):
        params = {}
        params.update({
            'category_id': category_id or 0,
            'language': 'en'
        })
        prepared_request = self.build_request('attribute_list',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              ** {
                                                  'params': params
                                              })
        sp_data_list = self.process_response('attribute_list', self.request(**prepared_request))
        return sp_data_list

    def get_attribute_list_tree(self, category_id_list=[]):
        params = {}
        params.update({
            'category_id_list': category_id_list or [],
            'language': 'en'
        })
        prepared_request = self.build_request('attribute_list_tree',
                                              self.sp_account.partner_id,
                                              self.sp_account.partner_key,
                                              self.sp_account.shop_id,
                                              self.sp_account.host,
                                              self.sp_account.access_token,
                                              **{
                                                  'params': params
                                              })
        sp_data_list = self.process_response('attribute_list_tree', self.request(**prepared_request))
        return sp_data_list