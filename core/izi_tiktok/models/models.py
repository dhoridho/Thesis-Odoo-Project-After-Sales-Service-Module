# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah
import logging
import time
import hashlib
import hmac
import json
from odoo import api, fields, models
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.addons.izi_marketplace.objects.utils.tools import mp, json_digger, generate_id
from odoo.addons.izi_tiktok.models.utils.account import TiktokAccount
from odoo.addons.izi_tiktok.models.utils.category import TiktokCategory
from odoo.addons.izi_tiktok.models.utils.promotion import TiktokPromotion
from odoo.addons.izi_tiktok.models.utils.shop import TiktokShop
from odoo.addons.izi_tiktok.models.utils.logistic import TiktokLogistic

_logger = logging.getLogger(__name__)

base_url = 'https://open-api.tiktokglobalshop.com'
auth_url = 'https://auth.tiktok-shops.com/oauth/authorize'
auth_base_url = 'https://auth.tiktok-shops.com'
# auth_state = 'IZITIKTOKSHOP'
auth_state = 'HMTIKTOKSHOP'



class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    tts_app_key = fields.Char(string='Tiktok App Key', required_if_marketplace="tiktok", states=READONLY_STATES)
    tts_app_secret = fields.Char(string='Tiktok App Secret', required_if_marketplace="tiktok", states=READONLY_STATES)
    tts_access_token = fields.Text(string='Tiktok Access Token', states=READONLY_STATES)
    tts_refresh_token = fields.Char(string='Tiktok Refresh Token', states=READONLY_STATES)
    tts_shop_id = fields.Many2one(comodel_name="mp.tiktok.shop", string="Tiktok Current Shop")
    tts_state_order_ids = fields.Many2many(
        comodel_name='mp.tiktok.state.order', string='Default Status Order',
        help='To get specific order from tiktok. Get all order if this field is empty.')

    # def _get_tts_seller_discount(self):
    #     return self.env.ref('izi_tiktok.product_tmpl_marketplace_seller_discount').product_variant_id.id
    # def _get_tts_platform_discount(self):
    #     return self.env.ref('izi_tiktok.product_tmpl_marketplace_platform_discount').product_variant_id.id
    # def _get_tts_shipping_fee_seller_discount(self):
    #     return self.env.ref('izi_tiktok.product_tmpl_marketplace_shipping_fee_seller_discount').product_variant_id.id
    # def _get_tts_shipping_fee_platform_discount(self):
    #     return self.env.ref('izi_tiktok.product_tmpl_marketplace_shipping_fee_platform_discount').product_variant_id.id

    tts_seller_discount_product_id = fields.Many2one('product.product', string="Default Seller Discount")
    tts_platform_discount_product_id = fields.Many2one('product.product', string="Default Platform Discount")
    tts_shipping_fee_seller_discount_product_id = fields.Many2one('product.product', string="Default Shipping Fee Subsidy form Seller")
    tts_shipping_fee_platform_discount_product_id = fields.Many2one('product.product', string="Default Shipping Fee Subsidy form Platform")

    def tiktok_generate_sign(self, path, params):
        params = params.copy()
        if 'sign' in params:
            del params['sign']
        if 'access_token' in params:
            del params['access_token']
        signstring = ''
        for key in params:
            signstring += (key + str(params[key]))
        signstring = '%s%s%s%s' % (
            self.tts_app_secret, path, signstring, self.tts_app_secret)
        sign = hmac.new(self.tts_app_secret.encode(), msg=signstring.encode(), digestmod=hashlib.sha256).hexdigest()
        return sign

    def tiktok_request(self, method, path, body, params={}):
        url = base_url + path
        if not params:
            timestamp = int(time.time())
            shop = self.env['mp.tiktok.shop'].search([('mp_account_id', '=', self.id)], limit=1)
            shop_id = shop.shop_id
            params = {
                'app_key': self.tts_app_key,
                'access_token': self.tts_access_token,
                'shop_id': shop_id,
                'timestamp': timestamp,
            }
            params.update({
                'sign': self.tiktok_generate_sign(path, params),
            })

        request_parameters = {
            'method': method,
            'url': url,
            'headers': {
                'Content-Length': '0',
                'User-Agent': 'PostmanRuntime/7.17.1',
                'Content-Type': 'application/json',
            },
            'params': params,
        }
        if body and body != None and body != {}:
            request_parameters['json'] = body
        response = requests.request(**request_parameters)
        response = response.json()
        return response

    # @api.multi
    def tiktok_authenticate(self):
        state = '%s%s' % (auth_state, str(self.id))
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '%s?app_key=%s&state=%s' % (auth_url, self.tts_app_key, state)
        }

    def tiktok_refresh_token(self):
        # _logger.info("Refresh token tiktok %s" % (self.id))
        url = auth_base_url + '/api/token/refreshToken'
        response = requests.request(**{
            'method': 'post',
            'url': url,
            'headers': {
                'Content-Length': '0',
                'User-Agent': 'PostmanRuntime/7.17.1',
                'Content-Type': 'application/json',
            },
            'json': {
                'app_key': self.tts_app_key,
                'app_secret': self.tts_app_secret,
                'refresh_token': self.tts_refresh_token,
                'grant_type': 'refresh_token',
            },
        })
        response = response.json()
        # _logger.info("Response refresh token tiktok - %s" % str(response))
        # Success
        if response.get('code') == 0:
            mp_token_obj = self.env['mp.token'].search([('mp_account_id', '=', self.id)])
            self.write({
                'tts_access_token': response['data']['access_token'],
                'tts_refresh_token': response['data']['refresh_token'],
                'state': 'authenticated',
            })
            expired_date = datetime.now() + relativedelta(seconds=response['data']['access_token_expire_in'])
            if mp_token_obj:
                mp_token_obj.sudo().write({
                    'name': response['data']['access_token'],
                    'refresh_token': response['data']['refresh_token'],
                    'expired_date': fields.Datetime.to_string(expired_date)
                })
            else:
                mp_token_obj.sudo().create({
                    'name': response['data']['access_token'],
                    'refresh_token': response['data']['refresh_token'],
                    'expired_date': fields.Datetime.to_string(expired_date),
                    'mp_account_id': self.id,
                    'tts_user_type': response['data']['user_type'],
                    'tts_open_id': response['data']['open_id'],
                    'raw': self.format_raw_data(response['data'])
                })
        else:
            self.write({
                'state': 'authenticating',
            })

    def format_raw_data(self, raw, indent=4):
        return json.dumps(raw, indent=indent)

    def tiktok_get_access_token(self, code):
        # _logger.info("Get access token tiktok %s - %s" % (self.id, code))
        url = auth_base_url + '/api/token/getAccessToken'
        response = requests.request(**{
            'method': 'post',
            'url': url,
            'headers': {
                'Content-Length': '0',
                'User-Agent': 'PostmanRuntime/7.17.1',
                'Content-Type': 'application/json',
            },
            'json': {
                'app_key': self.tts_app_key,
                'app_secret': self.tts_app_secret,
                'auth_code': code,
                'grant_type': 'authorized_code',
            },
        })
        response = response.json()
        # _logger.info("Response access token tiktok - %s" % str(response))
        # Success
        if response.get('code') == 0:
            self.write({
                'tts_access_token': response['data']['access_token'],
                'tts_refresh_token': response['data']['refresh_token'],
                'state': 'authenticated',
            })

    def tiktok_get_shop(self):
        mp_account_ctx = self.generate_context()
        tiktok_shop_obj = self.env['mp.tiktok.shop'].with_context(mp_account_ctx)
        tiktok_shop_rec = tiktok_shop_obj.search([])
        tiktok_shop_by_exid = {}
        for tiktok_shop in tiktok_shop_rec:
            tiktok_shop_by_exid[tiktok_shop.mp_external_id] = tiktok_shop

        path = '/api/shop/get_authorized_shop'
        url = base_url + path
        timestamp = int(time.time())
        params = {
            'app_key': self.tts_app_key,
            'access_token': self.tts_access_token,
            'timestamp': timestamp
        }
        params.update({
            'sign': self.tiktok_generate_sign(path, params),
        })
        response = requests.request(**{
            'method': 'get',
            'url': url,
            'headers': {
                'Content-Length': '0',
                'User-Agent': 'PostmanRuntime/7.17.1',
                'Content-Type': 'application/json',
                'x-tts-access-token': self.tts_access_token
            },
            'params': params,
        })
        response = response.json()
        # Success
        if response.get('code') == 0:
            data = response.get('data')
            if 'shop_list' in data:
                for shop in data['shop_list']:
                    vals = {
                        'shop_id': shop['shop_id'],
                        'shop_name': shop['shop_name'],
                        'region': shop['region'],
                        'type': str(shop['type']),
                        'mp_account_id': self.id,
                        'raw': json.dumps(shop, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': shop['shop_id'],
                    }
                    if shop['shop_id'] not in tiktok_shop_by_exid:
                        shop_rec = tiktok_shop_obj.create(vals)
                    else:
                        shop_rec = tiktok_shop_by_exid[shop['shop_id']]
                        shop_rec.write(vals)
                self.write({'tts_shop_id': shop_rec.id})

    @mp.tiktok.capture_error
    def v2_tiktok_get_shop(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tiktok_shop_obj = self.env['mp.tiktok.shop'].with_context(mp_account_ctx)
        tiktok_shop_rec = mp_tiktok_shop_obj.search([])
        tiktok_shop_by_exid = {}
        for tiktok_shop in tiktok_shop_rec:
            tiktok_shop_by_exid[tiktok_shop.mp_external_id] = tiktok_shop

        params = {}
        tts_data_raws, tts_data_sanitizeds = [], []
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        tts_account = self.tiktok_get_account(**params)
        tts_shop = TiktokShop(tts_account)
        tts_shop_raw = tts_shop.auth_shop()
        if not tts_shop_raw:
            raise UserError('Tiktok shop info is not found.')

        for shop in tts_shop_raw:
            if shop['seller_type'] == 'CROSS_BORDER':
                seller_type = '1'
            elif shop['seller_type'] == 'LOCAL':
                seller_type = '2'
            else:
                seller_type = None
            vals = {
                'shop_id': shop['id'],
                'shop_name': shop['name'],
                'shop_code': shop['code'],
                'shop_cipher': shop['cipher'],
                'region': shop['region'],
                'type': seller_type,
                'mp_account_id': self.id,
                'raw': json.dumps(shop, indent=4),
                'mp_external_id': shop['id'],
            }
            if shop['id'] not in tiktok_shop_by_exid:
                shop_rec = mp_tiktok_shop_obj.create(vals)
            else:
                shop_rec = tiktok_shop_by_exid[shop['id']]
                shop_rec.write(vals)
            self.write({'tts_shop_id': shop_rec.id})

        # tts_data_raw, tts_data_sanitized = mp_tiktok_shop_obj.with_context(
        #     mp_account_ctx)._prepare_mapping_raw_data(raw_data=tts_shop_raw)
        # check_existing_records_params = {
        #     'identifier_field': 'shop_id',
        #     'raw_data': tts_data_raw,
        #     'mp_data': tts_data_sanitized,
        #     'multi': isinstance(tts_data_sanitized, list)
        # }
        # check_existing_records = mp_tiktok_shop_obj.with_context(
        #     mp_account_ctx).check_existing_records(**check_existing_records_params)
        # mp_tiktok_shop_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def tiktok_get_dependencies(self):
        self.ensure_one()
        # self.tiktok_get_shop()
        self.v2_tiktok_get_shop()
        self.tiktok_get_warehouse()
        # self.v2_tiktok_get_warehouse()
        self.tiktok_get_logistics()
        # self.v2_tiktok_get_logistics()
        self.get_tiktok_brand()
        # self.tiktok_get_categories()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def tiktok_get_products(self, **kw):
        rec = self
        if kw.get('id', False):
            rec = self.browse(kw.get('id'))
        rec.ensure_one()
        MPProduct = self.env['mp.product']
        index = 0
        page_size = 100
        page_number = 1
        total = 1
        mp_account_ctx = self.generate_context()
        if kw.get('product_ids'):
            for product in kw.get('product_ids'):
                response = rec.tiktok_get_product_detail(product)
                if response.get('code') == 0:
                    product_by_external_id = MPProduct.tiktok_get_existing_products(rec.id)
                    product_detail = response.get('data')
                    mp_account_id = rec.id
                    mp_product_id = MPProduct.tiktok_product_save(
                        mp_account_id, product_detail, product_by_external_id)
                    ### create or update mp_stock for product
                    mp_stock_obj = self.env['mp.stock']
                    mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=product_detail)

                    # Get Existing Variant
                    variant_by_external_id = MPProduct.tiktok_get_existing_product_variants(mp_product_id)
                    MPProduct.tiktok_product_variant_save(
                        mp_account_id, mp_product_id, product_detail, variant_by_external_id)
                    ### create or update mp_stock for product variant
                    mp_stock_obj = self.env['mp.stock']
                    mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=product_detail,
                                                        map_type='variant')
        else:
            while (index < total):
                response = rec.tiktok_request('post', '/api/products/search', {
                    'page_size': page_size,
                    'page_number': page_number,
                    'search_status': 0,
                    'seller_sku_list': [],
                })
                # Success
                if response.get('code') == 0:
                    # Get Existing Product
                    product_by_external_id = MPProduct.tiktok_get_existing_products(rec.id)
                    # Get Product Detail
                    data = response.get('data')
                    for product in data['products']:
                        if product.get('status') == 4:
                            response = rec.tiktok_get_product_detail(product)
                            if response.get('code') == 0:
                                product_detail = response.get('data')
                                mp_account_id = rec.id
                                mp_product_id = MPProduct.tiktok_product_save(
                                    mp_account_id, product_detail, product_by_external_id)
                                ### create or update mp_stock for product
                                mp_stock_obj = self.env['mp.stock']
                                mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=product_detail)

                                # Get Existing Variant
                                variant_by_external_id = MPProduct.tiktok_get_existing_product_variants(mp_product_id)
                                MPProduct.tiktok_product_variant_save(
                                    mp_account_id, mp_product_id, product_detail, variant_by_external_id)
                                ### create or update mp_stock for product variant
                                mp_stock_obj = self.env['mp.stock']
                                mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=product_detail,
                                                                    map_type='variant')
                    total = data.get('total')
                    page_number += 1
                    index = (page_number-1)*page_size
                    if index >= total:
                        break
                else:
                    raise UserError(str(response))
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def tiktok_get_warehouse(self):
        mp_account_ctx = self.generate_context()
        tiktok_warehouse_obj = self.env['mp.tiktok.warehouse'].with_context(mp_account_ctx)
        tiktok_warehouse_rec = tiktok_warehouse_obj.search([])
        tiktok_warehouse_by_exid = {}
        for tiktok_warehouse in tiktok_warehouse_rec:
            tiktok_warehouse_by_exid[tiktok_warehouse.mp_external_id] = tiktok_warehouse

        response = self.tiktok_request('get', '/api/logistics/get_warehouse_list', {})
        # Success
        if response.get('code') == 0:
            data = response.get('data')
            if 'warehouse_list' in data:
                for warehouse in data['warehouse_list']:
                    vals = {
                        'warehouse_id': warehouse['warehouse_id'],
                        'warehouse_name': warehouse['warehouse_name'],
                        'warehouse_type': str(warehouse['warehouse_type']),
                        'warehouse_sub_type': str(warehouse['warehouse_sub_type']),
                        'warehouse_effect_status': str(warehouse['warehouse_effect_status']),
                        'region': warehouse['warehouse_address']['region'],
                        'state': warehouse['warehouse_address']['state'],
                        'city': warehouse['warehouse_address']['city'],
                        'district': warehouse['warehouse_address']['district'],
                        'town': warehouse['warehouse_address']['town'],
                        'zipcode': warehouse['warehouse_address']['zipcode'],
                        'phone': warehouse['warehouse_address']['phone'],
                        'contact_person': warehouse['warehouse_address']['contact_person'],
                        'mp_account_id': self.id,
                        'raw': json.dumps(warehouse, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': warehouse['warehouse_id'],
                    }
                    if warehouse['warehouse_id'] not in tiktok_warehouse_by_exid:
                        warehouse_rec = tiktok_warehouse_obj.create(vals)
                    else:
                        warehouse_rec = tiktok_warehouse_by_exid[warehouse['warehouse_id']]
                        warehouse_rec.write(vals)

    def v2_tiktok_get_warehouse(self):
        mp_account_ctx = self.generate_context()
        tiktok_warehouse_obj = self.env['mp.tiktok.warehouse'].with_context(mp_account_ctx)
        tiktok_warehouse_rec = tiktok_warehouse_obj.search([])
        tiktok_warehouse_by_exid = {}
        for tiktok_warehouse in tiktok_warehouse_rec:
            tiktok_warehouse_by_exid[tiktok_warehouse.mp_external_id] = tiktok_warehouse

        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        tts_account = self.tiktok_get_account(**params)
        tts_logistic = TiktokLogistic(tts_account)
        tts_logistic_raw = tts_logistic.get_warehouse_list()
        # Success
        if tts_logistic_raw:
            if 'warehouse_list' in tts_logistic_raw:
                for warehouse in tts_logistic_raw['warehouse_list']:
                    vals = {
                        'warehouse_id': warehouse['warehouse_id'],
                        'warehouse_name': warehouse['warehouse_name'],
                        'warehouse_type': str(warehouse['warehouse_type']),
                        'warehouse_sub_type': str(warehouse['warehouse_sub_type']),
                        'warehouse_effect_status': str(warehouse['warehouse_effect_status']),
                        'region': warehouse['warehouse_address']['region'],
                        'state': warehouse['warehouse_address']['state'],
                        'city': warehouse['warehouse_address']['city'],
                        'district': warehouse['warehouse_address']['district'],
                        'town': warehouse['warehouse_address']['town'],
                        'zipcode': warehouse['warehouse_address']['zipcode'],
                        'phone': warehouse['warehouse_address']['phone'],
                        'contact_person': warehouse['warehouse_address']['contact_person'],
                        'mp_account_id': self.id,
                        'raw': json.dumps(warehouse, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': warehouse['warehouse_id'],
                    }
                    if warehouse['warehouse_id'] not in tiktok_warehouse_by_exid:
                        warehouse_rec = tiktok_warehouse_obj.create(vals)
                    else:
                        warehouse_rec = tiktok_warehouse_by_exid[warehouse['warehouse_id']]
                        warehouse_rec.write(vals)

    def tiktok_get_product_detail(self, product):
        # Custom Parameters
        path = '/api/products/details'
        product_id = product.get('id')
        timestamp = int(time.time())
        params = {
            'app_key': self.tts_app_key,
            'access_token': self.tts_access_token,
            'product_id': product_id,   
            'timestamp': timestamp,
        }
        params.update({
            'sign': self.tiktok_generate_sign(path, params),
        })
        response = self.tiktok_request('get', path, {}, params)
        return response

    def tiktok_get_categories_v1(self):
        mp_account_ctx = self.generate_context()
        tiktok_category_obj = self.env['mp.tiktok.product.category'].with_context(mp_account_ctx)
        tiktok_category_rec = tiktok_category_obj.search([])
        tiktok_category_by_exid = {}
        for tiktok_category in tiktok_category_rec:
            tiktok_category_by_exid[tiktok_category.mp_external_id] = tiktok_category

        response = self.tiktok_request('get', '/api/products/categories', {})
        # Success
        if response.get('code') == 0:
            data = response.get('data')
            if 'category_list' in data:
                for category in data['category_list']:
                    vals = {
                        'category_id': category['id'],
                        'parent_id': category['parent_id'],
                        'local_display_name': category['local_display_name'],
                        'is_leaf': category['is_leaf'],
                        'mp_account_id': self.id,
                        'raw': json.dumps(category, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': category['id'],
                    }
                    if category['id'] not in tiktok_category_by_exid:
                        category_rec = tiktok_category_obj.create(vals)
                    else:
                        category_rec = tiktok_category_by_exid[category['id']]
                        category_rec.write(vals)

    @api.model
    def tiktok_get_account(self, **kwargs):
        credentials = dict({
            'app_key': self.tts_app_key,
            'app_secret': self.tts_app_secret,
            'shop_id': int(self.tts_shop_id.shop_id),
            'shop_cipher': self.tts_shop_id.shop_cipher,
            'auth_code': self.mp_token_id.tts_auth_code,
            'access_token': self.tts_access_token,
            'refresh_token': self.tts_refresh_token,
            'expired_date': fields.Datetime.from_string(self.access_token_expired_date)
        }, **kwargs)
        tiktok_account = TiktokAccount(**credentials)
        return tiktok_account

    @mp.tiktok.capture_error
    def tiktok_get_categories(self):
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        mp_category_obj = self.env['mp.tiktok.product.category'].with_context(mp_account_ctx)

        self.ensure_one()

        tiktok_account = self.tiktok_get_account()
        tiktok_category = TiktokCategory(tiktok_account, api_version="v2",
                                        sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing category from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        tts_raw, tts_data = tiktok_category.get_category_info(shop_id=self.tts_shop_id.shop_id)
        mp_data_raw = mp_category_obj.tts_generate_category_data(tts_raw, mp_account_id)
        tp_data_raw, tp_data_sanitized = mp_category_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)

        check_existing_records_params = {
            'identifier_field': 'category_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_category_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_category_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        return tp_data_raw, tp_data_sanitized

    def tiktok_get_sale_order(self, **kwargs):
        rec = self
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(mp_account_ctx)
        if kwargs.get('params', False) == 'by_mp_invoice_number':
            self.tiktok_process_single_order(kwargs.get('mp_invoice_number'))
            return True
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        tts_orders_by_mpexid = {}
        tts_orders = order_obj.search([('mp_account_id', '=', self.id)])
        for tts_order in tts_orders:
            tts_orders_by_mpexid[tts_order.mp_invoice_number] = tts_order

        if kwargs.get('params') == 'by_date_range':
            update_time_from = int(datetime.timestamp(kwargs.get('from_date')))
            update_time_to = int(datetime.timestamp(kwargs.get('to_date')))
            more = True
            cursor = False
            index = 0
            order_data_raw = []
            force_update_ids = []
            while (more):
                params = {
                    'page_size': 50,
                    'update_time_from': update_time_from,
                    'update_time_to': update_time_to,
                    # 'order_status': 140,
                    # 'cursor': '',
                }
                if cursor:
                    params['cursor'] = cursor
                elif index > 0:
                    raise UserError('No Cursor Found')

                response = self.tiktok_request('post', '/api/orders/search', params)
                # Success
                if response.get('code') == 0:
                    data = response.get('data')
                    more = data.get('more')
                    cursor = data.get('next_cursor')

                    order_id_list = []
                    if data.get('total'):
                        for data_order in data.get('order_list', 0):
                            order_status = data_order['order_status']
                            if data_order['order_id'] in tts_orders_by_mpexid:
                                existing_order = tts_orders_by_mpexid[data_order['order_id']]
                                mp_status_changed = existing_order.tts_order_status != str(order_status)
                                if mp_status_changed:
                                    order_id_list.append(data_order['order_id'])
                                elif mp_account_ctx.get('force_update'):
                                    force_update_ids.append(existing_order.id)
                                    order_id_list.append(data_order['order_id'])
                                else:
                                    continue
                            else:
                                existing_order = False
                                mp_status_changed = False
                                if order_status == 140 and not self.get_cancelled_orders:
                                    continue
                                if order_status == 100 and not self.get_unpaid_orders:
                                    continue
                                state_order = rec.tts_state_order_ids.mapped('code')  # for specific status order
                                allowed_order = order_status in state_order if state_order else order_status
                                if allowed_order:
                                    order_id_list.append(data_order['order_id'])

                        # Get Order Detail
                        response_order_detail = self.tiktok_request('post', '/api/orders/detail/query', {
                            'order_id_list': order_id_list,
                        })
                        if response_order_detail.get('code') == 0:
                            detail_data = response_order_detail.get('data')
                            order_data_raw.extend(detail_data['order_list'])
                    else:
                        more = False
                        break
                else:
                    more = False
                    break

                index += 1
            self.tiktok_mapping_orders(order_data_raw, force_update_ids)
        elif kwargs.get('by_mp_invoice_number'):
            self.tiktok_process_single_order(kwargs.get('mp_invoice_number'))

    def tiktok_get_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_range = kwargs.get('time_range', False)
        if time_range:
            if time_range == 'last_hour':
                from_time = datetime.now() - timedelta(hours=1)
                to_time = datetime.now()
            elif time_range == 'last_3_days':
                from_time = datetime.now() - timedelta(days=3)
                to_time = datetime.now()
            kwargs.update({
                'from_date': from_time,
                'to_date': to_time
            })
        rec.tiktok_get_sale_order(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def tiktok_mapping_orders(self, order_data_raw, force_update_ids):
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(mp_account_ctx)
        # Start mapping order data
        tts_order_raws, tts_order_sanitizeds = [], []
        for data in order_data_raw:
            tts_order_data_raw, tts_order_data_sanitized = order_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
            tts_order_raws.append(tts_order_data_raw)
            tts_order_sanitizeds.append(tts_order_data_sanitized)

        if force_update_ids:
            order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                'force_update_ids': force_update_ids
            }))

        if tts_order_raws and tts_order_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'tts_order_id',
                'raw_data': tts_order_raws,
                'mp_data': tts_order_sanitizeds,
                'multi': isinstance(tts_order_sanitizeds, list)
            }
            check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def tiktok_process_single_order(self, tts_order_id, sale_order=False):
        response_order_detail = self.tiktok_request('post', '/api/orders/detail/query', {
            'order_id_list': [tts_order_id],
        })
        if response_order_detail.get('code') == 0:
            order_data_raw = response_order_detail.get('data').get('order_list')
            force_ids = []
            if sale_order:
                force_ids = [sale_order.id]
            self.tiktok_mapping_orders(order_data_raw, force_ids)

    def tiktok_ship_order(self, sale_order):
        response_ship_order = self.tiktok_request('post', '/api/fulfillment/rts', {
            'package_id': sale_order.tts_package_id,
        })
        if response_ship_order.get('code') == 0:
            sale_order.action_confirm()
            self.tiktok_process_single_order(sale_order.tts_order_id, sale_order)

    def tiktok_print_label(self, sale_order):
        res = {
            'message': 'Cannot Print Label',
            'url': False,
        }
        # Custom Parameters
        path = '/api/logistics/shipping_document'
        order_id = sale_order.tts_order_id
        timestamp = int(time.time())
        params = {
            'app_key': self.tts_app_key,
            'access_token': self.tts_access_token,
            'document_type': 'SHIPPING_LABEL',
            'order_id': order_id,
            'timestamp': timestamp,
        }
        params.update({
            'sign': self.tiktok_generate_sign(path, params),
        })
        response = self.tiktok_request('get', path, {}, params)
        if response.get('code') == 0:
            if response.get('data'):
                res.update({
                    'message': False,
                    'url': response.get('data').get('doc_url'),
                })
        else:
            if response.get('message'):
                res.update({
                    'message': response.get('message'),
                })
        return res

    def tiktok_get_logistics(self):
        # mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        mp_delivery_product_tmpl = self.env['product.template'].search([('name', '=', 'Marketplace Delivery')], limit=1)
        mp_account_ctx = self.generate_context()
        tiktok_logistic_obj = self.env['mp.tiktok.logistic'].with_context(mp_account_ctx)
        tiktok_logistic_record = self.env['mp.tiktok.logistic']
        tiktok_logistic_provider_obj = self.env['mp.tiktok.logistic.provider'].with_context(mp_account_ctx)
        tiktok_logistic_rec = tiktok_logistic_obj.search([('shop_id', '=', self.tts_shop_id.id)])
        tiktok_logistic_by_exid = {}
        for tiktok_logistic in tiktok_logistic_rec:
            tiktok_logistic_by_exid[tiktok_logistic.mp_external_id] = tiktok_logistic

        response = self.tiktok_request('get', '/api/logistics/shipping_providers', {})

        if response.get('code') == 0:
            data = response.get('data')
            for logistic in data['delivery_option_list']:
                vals = {
                    'delivery_option_id': logistic['delivery_option_id'],
                    'delivery_option_name': logistic['delivery_option_name'],
                    'item_max_weight': logistic['item_weight_limit']['max_weight'],
                    'item_min_weight': logistic['item_weight_limit']['min_weight'],
                    'item_dimension_length_limit': logistic['item_dimension_limit']['length'],
                    'item_dimension_width_limit': logistic['item_dimension_limit']['width'],
                    'item_dimension_height_limit': logistic['item_dimension_limit']['height'],
                    'shop_id': self.tts_shop_id.id,
                    'mp_account_id': self.id,
                    'raw': json.dumps(logistic, indent=4),
                    # 'md5sign': self.generate_signature(shop),
                    'mp_external_id': logistic['delivery_option_id'],
                    'product_id': mp_delivery_product_tmpl.product_variant_id.id if mp_delivery_product_tmpl else False
                }
                if logistic['delivery_option_id'] not in tiktok_logistic_by_exid:
                    tiktok_logistic_record |= tiktok_logistic_obj.create(vals)
                else:
                    logistic_rec = tiktok_logistic_by_exid[logistic['delivery_option_id']]
                    logistic_rec.write(vals)
                    tiktok_logistic_record |= logistic_rec

            for record in tiktok_logistic_record:
                tiktok_logistic_provider_rec = tiktok_logistic_provider_obj.search([('logistic_id', '=', record.id)])
                tiktok_logistic_provider_by_exid = {}
                for tiktok_logistic_provider in tiktok_logistic_provider_rec:
                    tiktok_logistic_provider_by_exid[tiktok_logistic_provider.mp_external_id] = tiktok_logistic_provider
                tts_logistic_raw = json.loads(record.raw, strict=False)
                tts_logistic_provider = [dict(tp_logistic_service, **dict([('logistic_id', record.id)])) for
                                         tp_logistic_service in tts_logistic_raw['shipping_provider_list']]

                for logistic_provier in tts_logistic_provider:
                    vals = {
                        'shipping_provider_id': logistic_provier['shipping_provider_id'],
                        'shipping_provider_name': logistic_provier['shipping_provider_name'],
                        'mp_account_id': self.id,
                        'raw': json.dumps(logistic_provier, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': logistic_provier['shipping_provider_id'],
                        'logistic_id': logistic_provier['logistic_id'],
                        'product_id': mp_delivery_product_tmpl.product_variant_id.id if mp_delivery_product_tmpl else False,
                    }
                    if logistic_provier['shipping_provider_id'] not in tiktok_logistic_provider_by_exid:
                        logistic_provider_rec = tiktok_logistic_provider_obj.create(vals)
                    else:
                        logistic_provider_rec = tiktok_logistic_provider_by_exid[logistic_provier['shipping_provider_id']]
                        logistic_provider_rec.write(vals)

    def v2_tiktok_get_logistics(self):
        mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        mp_account_ctx = self.generate_context()
        tiktok_logistic_obj = self.env['mp.tiktok.logistic'].with_context(mp_account_ctx)
        tiktok_logistic_record = self.env['mp.tiktok.logistic']
        tiktok_logistic_provider_obj = self.env['mp.tiktok.logistic.provider'].with_context(mp_account_ctx)
        tiktok_logistic_rec = tiktok_logistic_obj.search([('shop_id', '=', self.tts_shop_id.id)])
        tiktok_logistic_by_exid = {}
        for tiktok_logistic in tiktok_logistic_rec:
            tiktok_logistic_by_exid[tiktok_logistic.mp_external_id] = tiktok_logistic

        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        tts_account = self.tiktok_get_account(**params)
        tts_logistic = TiktokLogistic(tts_account)
        tts_logistic_raw = tts_logistic.get_logistic_info()

        response = self.tiktok_request('get', '/api/logistics/shipping_providers', {})

        if tts_logistic_raw:
            if 'delivery_option_list' in tts_logistic_raw:
                for logistic in tts_logistic_raw['delivery_option_list']:
                    vals = {
                        'delivery_option_id': logistic['delivery_option_id'],
                        'delivery_option_name': logistic['delivery_option_name'],
                        'item_max_weight': logistic['item_weight_limit']['max_weight'],
                        'item_min_weight': logistic['item_weight_limit']['min_weight'],
                        'item_dimension_length_limit': logistic['item_dimension_limit']['length'],
                        'item_dimension_width_limit': logistic['item_dimension_limit']['width'],
                        'item_dimension_height_limit': logistic['item_dimension_limit']['height'],
                        'shop_id': self.tts_shop_id.id,
                        'mp_account_id': self.id,
                        'raw': json.dumps(logistic, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': logistic['delivery_option_id'],
                        'product_id': mp_delivery_product_tmpl.product_variant_id.id if mp_delivery_product_tmpl else False
                    }
                    if logistic['delivery_option_id'] not in tiktok_logistic_by_exid:
                        tiktok_logistic_record |= tiktok_logistic_obj.create(vals)
                    else:
                        logistic_rec = tiktok_logistic_by_exid[logistic['delivery_option_id']]
                        logistic_rec.write(vals)
                        tiktok_logistic_record |= logistic_rec

            if tiktok_logistic_record:
                for record in tiktok_logistic_record:
                    tiktok_logistic_provider_rec = tiktok_logistic_provider_obj.search([('logistic_id', '=', record.id)])
                    tiktok_logistic_provider_by_exid = {}
                    for tiktok_logistic_provider in tiktok_logistic_provider_rec:
                        tiktok_logistic_provider_by_exid[tiktok_logistic_provider.mp_external_id] = tiktok_logistic_provider
                    tts_logistic_raw = json.loads(record.raw, strict=False)
                    tts_logistic_provider = [dict(tp_logistic_service, **dict([('logistic_id', record.id)])) for
                                             tp_logistic_service in tts_logistic_raw['shipping_provider_list']]

                    for logistic_provier in tts_logistic_provider:
                        vals = {
                            'shipping_provider_id': logistic_provier['shipping_provider_id'],
                            'shipping_provider_name': logistic_provier['shipping_provider_name'],
                            'mp_account_id': self.id,
                            'raw': json.dumps(logistic_provier, indent=4),
                            # 'md5sign': self.generate_signature(shop),
                            'mp_external_id': logistic_provier['shipping_provider_id'],
                            'logistic_id': logistic_provier['logistic_id'],
                            'product_id': mp_delivery_product_tmpl.product_variant_id.id if mp_delivery_product_tmpl else False,
                        }
                        if logistic_provier['shipping_provider_id'] not in tiktok_logistic_provider_by_exid:
                            logistic_provider_rec = tiktok_logistic_provider_obj.create(vals)
                        else:
                            logistic_provider_rec = tiktok_logistic_provider_by_exid[logistic_provier['shipping_provider_id']]
                            logistic_provider_rec.write(vals)

    def get_tiktok_brand(self):
        mp_account_ctx = self.generate_context()
        tiktok_brand_obj = self.env['mp.tiktok.brand'].with_context(mp_account_ctx)
        tiktok_brand_rec = tiktok_brand_obj.search([])
        tiktok_brand_by_exid = {}
        for tiktok_brand in tiktok_brand_rec:
            tiktok_brand_by_exid[tiktok_brand.mp_external_id] = tiktok_brand

        response = self.tiktok_request('get', '/api/products/brands', {})
        # Success
        if response.get('code') == 0:
            data = response.get('data')
            if 'brand_list' in data:
                for brand in data['brand_list']:
                    vals = {
                        'brand_id': brand['id'],
                        'brand_name': brand['name'],
                        'mp_account_id': self.id,
                        'raw': json.dumps(brand, indent=4),
                        # 'md5sign': self.generate_signature(shop),
                        'mp_external_id': brand['id'],
                    }
                    if brand['id'] not in tiktok_brand_by_exid:
                        brand_rec = tiktok_brand_obj.create(vals)
                    else:
                        brand_rec = tiktok_brand_by_exid[brand['id']]
                        brand_rec.write(vals)

    def tiktok_set_product(self, **kw):
        self.ensure_one()
        mp_product_ids = []

        if kw.get('mode') == 'stock_only':
            base_payload = {
                'product_id': '',
                'skus': []
            }
            try:
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        base_payload.update({
                            'product_id': data['product_obj'].mp_external_id
                        })
                        base_payload['skus'].append({
                            'stock_infos': [{
                                'available_stock': data['stock']
                            }]
                        })
                        mp_product_ids.append({'id': data['product_obj'].mp_external_id})
                    elif data['product_obj']._name == 'mp.product.variant':
                        base_payload.update({
                            'product_id': data['product_obj'].mp_product_id.mp_external_id
                        })
                        base_payload['skus'].append({
                            'id': data['product_obj'].mp_external_id,
                            'stock_infos': [{
                                'available_stock': data['stock']
                            }]
                        })
                        mp_product_ids.append({'id': data['product_obj'].mp_product_id.mp_external_id})
                response = self.tiktok_request('put', '/api/products/stocks', base_payload)
                self.tiktok_get_products(**{'product_ids': mp_product_ids})
            except Exception as e:
                pass
        if kw.get('mode') == 'price_only':
            base_payload = {
                'product_id': '',
                'skus': []
            }
            try:
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        base_payload.update({
                            'product_id': data['product_obj'].mp_external_id
                        })
                        base_payload['skus'].append({
                            'original_price': data['price']
                        })
                        mp_product_ids.append({'id': data['product_obj'].mp_external_id})
                    elif data['product_obj']._name == 'mp.product.variant':
                        base_payload.update({
                            'product_id': data['product_obj'].mp_product_id.mp_external_id
                        })
                        base_payload['skus'].append({
                            'id': data['product_obj'].mp_external_id,
                            'original_price': str(data['price'])
                        })
                        mp_product_ids.append({'id': data['product_obj'].mp_product_id.mp_external_id})
                response = self.tiktok_request('put', '/api/products/prices', base_payload)
                self.tiktok_get_products(**{'product_ids': mp_product_ids})
            except Exception as e:
                pass
        if kw.get('mode') == 'activation':
            try:
                for data in kw.get('data', []):
                    base_payload = {
                        'product_ids': [data['product_obj'].mp_external_id]
                    }
                    if data['product_obj']._name == 'mp.product.variant':
                        base_payload.update({'product_ids': [data['product_obj'].mp_product_id.mp_external_id]})
                    path = '/api/products/activate' if data['activate'] else '/api/products/inactivated_products'
                    response = self.tiktok_request('post', path, base_payload)
                    data['product_obj'].write({'active': data['activate']})
            except Exception as e:
                pass
        if kw.get('mode') == 'detail':
            # Mandatory field
            base_payload = {
                'product_id': '',
                'product_name': '',
                'description': '',
                'category_id': '',
                'package_weight': '',
                'skus': [],
                'images': []
            }
            try:
                for data in kw.get('data', []):
                    if len(data.name) < 25:
                        raise UserError('Product name must have at least 25 Character')
                    
                    base_payload.update({
                        'product_id': data.mp_product_id.mp_external_id,
                        'product_name': data.name,
                        'description': data.description,
                        'category_id': data.mp_product_id.tts_pd_category,
                        'package_weight': data.weight,
                        'product_attributes': []
                    })
                    variants = data.mp_product_id.mp_product_variant_ids
                    for var in variants:
                        sku_payload = {
                            'id' : var.mp_external_id,
                            'original_price': var.list_price,
                            'seller_sku': var.default_code if len(data.mp_product_id.mp_product_variant_ids) > 1 else data.sku,
                            'stock_infos': []
                        }
                        # stock
                        for stock in var.stock_ids:
                            stock_vals = {
                                'warehouse_id': stock.warehouse_id.mp_external_id,
                                'available_stock': stock.tts_var_stock
                            }
                            sku_payload['stock_infos'].append(stock_vals)
                        
                        base_payload['skus'].append(sku_payload)
                    
                    # attributes
                    for attr in data.mp_product_id.tts_product_attribute_ids:
                        pd_attribute_vals = {
                            'attribute_id': attr.mp_external_id,
                            'attribute_values': []
                        }
                        for attr_value in attr.value_ids:
                            pd_attribute_vals['attribute_values'].append({
                                'value_id': attr_value.value_id,
                                'value_name': attr_value.name
                            })
                        base_payload['product_attributes'].append(pd_attribute_vals)

                    # images
                    for image in data.mp_product_id.mp_product_image_ids:
                        image_vals = {
                            'id': image.mp_external_id
                        }
                        base_payload['images'].append(image_vals)
                    # else:
                    #     base_payload.update({
                    #         'product_id': data['product_obj'].mp_product_id.mp_external_id
                    #     })
                    #     base_payload['skus'].append({
                    #         'id': data['product_obj'].mp_external_id,
                    #         'original_price': data['price']
                    #     })
                    mp_product_ids.append({'id': data.mp_product_id.mp_external_id})
                    response = self.tiktok_request('put', '/api/products', base_payload)
                    if response.get('message') != 'Success':
                        raise UserError(response.get('message'))
                # time.sleep(15)
                self.tiktok_get_products(**{'product_ids': mp_product_ids})
            except Exception as e:
                raise UserError(str(e))

    def tiktok_get_promotion(self, **kw):
        self.ensure_one()
        params = {}
        mp_account_ctx = self.generate_context()
        mp_promotion_obj = self.env['mp.promotion.program']
        _notify = self.env['mp.base']._notify

        # fetch all exist sp promotion data
        tts_promotion_by_mpexid = {}
        tts_promotion_recs = mp_promotion_obj.search(
            [('mp_account_id', '=', self.id), ('company_id', '=', self.company_id.id)])
        for tts_promotion_rec in tts_promotion_recs:
            tts_promotion_by_mpexid[tts_promotion_rec.tts_promotion_id] = tts_promotion_rec
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
            tts_account = self.tiktok_get_account(**params)
            tts_promotion = TiktokPromotion(tts_account)
            kw.update({
                'tts_promotion': tts_promotion,
                'mp_account_ctx': mp_account_ctx,
                'tts_promotion_by_mpexid': tts_promotion_by_mpexid
            })

            self.tiktok_get_discount_promotion(**kw)
            # self.tiktok_get_coupon_promotion(**kw)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def tiktok_get_discount_promotion(self, **kw):
        _logger = self.env['mp.base']._logger
        tts_promotion = kw.get('tts_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        mp_account_ctx.update({
            'force_update': True
        })
        mp_promotion_obj = self.env['mp.promotion.program']
        tts_promotion_by_mpexid = kw.get('tts_promotion_by_mpexid')

        tts_discount_raws, tts_discount_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': ['NOT_START', 'ONGOING'],
                # 'status': [1, 2],  ### Available value: 1.upcoming / 2.ongoing / 3.expired / 4.deactivated.
                # 'title': 'Discount'
            }
            tts_discount_list = tts_promotion.get_promotion_list(**params)
            if 'message' in tts_discount_list and tts_discount_list.get('message') != '':
                raise UserError('Tiktok API error with the code: %s caused by %s' % (
                tts_discount_list.get('code'), tts_discount_list.get('message')))
            if tts_discount_list:
                for index, tts_data_discount in enumerate(tts_discount_list):
                    raw_data_detail = tts_promotion.get_promotion_detail(promotion_id=tts_data_discount.get('promotion_id'))
                    if 'message' in raw_data_detail and raw_data_detail.get('message') != '':
                        raise UserError('Tiktok API error with the code: %s caused by %s' % (
                            raw_data_detail.get('code'), raw_data_detail.get('message')))
                    if raw_data_detail:
                        raw_data_detail.update({
                            # mapping base info promotion
                            'base_info': {
                                'type': 'discount',
                                'name': raw_data_detail['title'],
                                'status': raw_data_detail['status'],
                                'start_time': raw_data_detail['begin_time'],
                                'end_time': raw_data_detail['end_time'],
                                'promotion_id': raw_data_detail['promotion_id']
                            },
                            # mapping spesific type promotion fields
                            'discount': {
                                'item_list': raw_data_detail['product_list']
                            },
                            'voucher': {},
                            'bundle': {},
                            'addon': {}
                        })

                        # cleaning key after mapping
                        raw_data_detail.pop('promotion_list')
                        # raw_data_detail.pop('more')

                        tts_discount_data_raw, tts_discount_data_sanitized = mp_promotion_obj.with_context(
                            mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
                        tts_discount_raws.append(tts_discount_data_raw)
                        tts_discount_sanitizeds.append(tts_discount_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting promotion detail of %s... Please wait!" % (
                mp_promotion_id
            )
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
            raw_data_detail = tts_promotion.get_promotion_detail(discount_id=mp_promotion_id)
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'discount',
                    'name': raw_data_detail['title'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['begin_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['promotion_id']
                },
                # mapping spesific type promotion fields
                'discount': {
                    'item_list': raw_data_detail['promotion_list']
                },
                'voucher': {}
            })

            # cleaning key after mapping
            raw_data_detail.pop('promotion_list')
            # raw_data_detail.pop('more')

            tts_discount_data_raw, tts_discount_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
            tts_discount_raws.append(tts_discount_data_raw)
            tts_discount_sanitizeds.append(tts_discount_data_sanitized)

        if tts_discount_raws and tts_discount_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'tts_promotion_id',
                'raw_data': tts_discount_raws,
                'mp_data': tts_discount_sanitizeds,
                'multi': isinstance(tts_discount_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def tiktok_get_coupon_promotion(self, **kw):
        _logger = self.env['mp.base']._logger
        tts_promotion = kw.get('tts_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        mp_account_ctx.update({
            'force_update': True
        })
        mp_promotion_obj = self.env['mp.promotion.program']
        tts_promotion_by_mpexid = kw.get('tts_promotion_by_mpexid')

        tts_discount_raws, tts_discount_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': [1, 2],  ### Available value: 1.upcoming / 2.ongoing / 3.expired / 4.deactivated.
                'title': 'Voucher'
            }
            tts_discount_list = tts_promotion.get_promotion_list(**params)
            if 'message' in tts_discount_list and tts_discount_list.get('message') != '':
                raise UserError('Tiktok API error with the code: %s caused by %s' % (
                tts_discount_list.get('error'), tts_discount_list.get('message')))
            if tts_discount_list:
                for index, tts_data_discount in enumerate(tts_discount_list):
                    notif_msg = "(%s/%d) Getting discount detail of %s... Please wait!" % (
                        str(index + 1), len(tts_discount_list), tts_data_discount.get('discount_id')
                    )
                    # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    raw_data_detail = tts_promotion.get_promotion_detail(discount_id=tts_data_discount.get('discount_id'))
                    raw_data_detail.update({
                        # mapping base info promotion
                        'base_info': {
                            'type': 'voucher',
                            'name': raw_data_detail['discount_name'],
                            'status': raw_data_detail['status'],
                            'start_time': raw_data_detail['start_time'],
                            'end_time': raw_data_detail['end_time'],
                            'promotion_id': raw_data_detail['promotion_id']
                        },
                        # mapping spesific type promotion fields
                        'discount': {},
                        'voucher': {
                            'item_list': raw_data_detail['item_list']
                        }
                    })

                    # cleaning key after mapping
                    raw_data_detail.pop('item_list')
                    raw_data_detail.pop('more')

                    tts_discount_data_raw, tts_discount_data_sanitized = mp_promotion_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
                    tts_discount_raws.append(tts_discount_data_raw)
                    tts_discount_sanitizeds.append(tts_discount_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting promotion detail of %s... Please wait!" % (
                mp_promotion_id
            )
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
            raw_data_detail = tts_promotion.get_discount(discount_id=mp_promotion_id)
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'voucher',
                    'name': raw_data_detail['discount_name'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['start_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['discount_id']
                },
                # mapping spesific type promotion fields
                'discount': {},
                'voucher': {
                    'item_list': raw_data_detail['item_list']
                }
            })

            # cleaning key after mapping
            raw_data_detail.pop('item_list')
            raw_data_detail.pop('more')

            tts_discount_data_raw, tts_discount_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
            tts_discount_raws.append(tts_discount_data_raw)
            tts_discount_sanitizeds.append(tts_discount_data_sanitized)

        if tts_discount_raws and tts_discount_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'tts_promotion_id',
                'raw_data': tts_discount_raws,
                'mp_data': tts_discount_sanitizeds,
                'multi': isinstance(tts_discount_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def tiktok_get_orders_wallet(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_range = kwargs.get('time_range', False)
        if time_range:
            if time_range == 'last_30_minutes':
                new_datetime = datetime.now() - timedelta(minutes=30)
                from_time = new_datetime - timedelta(minutes=30)
                to_time = new_datetime
            elif time_range == 'last_hours':
                new_datetime = datetime.now() - timedelta(hours=1)
                from_time = new_datetime - timedelta(minutes=30)
                to_time = new_datetime
            kwargs.update({
                'from_date': from_time,
                'to_date': to_time
            })
        bank_statement = rec.tiktok_get_saldo_history(**kwargs)
        if kwargs.get('mode') in ['reconcile_only', 'both']:
            bank_statement_list = [data['name'] for data in bank_statement]
            auto_rec_param = {'bank_statement_list': bank_statement_list}
            rec.tiktok_auto_reconcile(**auto_rec_param)
        mp_account_ctx = rec.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        cron_name = 'IZI Tiktok Wallet Scheduler %s' % (str(mp_account_id))
        cron_wallet = self.env['ir.cron'].sudo().search([('name', '=', cron_name), ('active', '=', False)])
        delta_var = 'seconds'
        interval = 10
        next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
        if cron_wallet:
            cron_wallet.sudo().write({
                'nextcall': next_call,
                'active': True
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @mp.tiktok.capture_error
    def tiktok_get_saldo_history(self, **kwargs):
        mp_account_ctx = self.generate_context()
        account_bank_statement_obj = self.env['account.bank.statement'].with_context(
            dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        mp_account_ctx.update({
            'force_update': True
        })
        self.ensure_one()

        # _notify('info', 'Importing order wallet from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        total_days = (to_date - from_date).days
        bank_statement_raw = []
        if total_days == 0:
            from_date_str = from_date.strftime("%Y/%m/%d %H:%M:%S")
            to_date_str = to_date.strftime("%Y/%m/%d %H:%M:%S")
            bank_statement_raw.append({
                'name': 'Tiktok Saldo: %s' % ((from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                'date': (from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                'journal_id': self.wallet_journal_id.id,
                'mp_start_date': from_date_str,
                'mp_end_date': to_date_str
            })
        else:
            for index in range(0, total_days):
                # new_from_date = from_date + relativedelta(days=index)
                # new_to_date = from_date + relativedelta(days=index, hours=24)
                #### -7 agar data yang didapatkan sesuai dengan display dari tiktok
                new_from_date = from_date + relativedelta(days=index, hours=-7)
                new_to_date = from_date + relativedelta(days=index, hours=17)
                if new_to_date.day == to_date.day:
                    new_to_date = to_date
                bank_statement_raw.append({
                    'name': 'Tiktok Saldo: %s' % ((new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                    'date': (new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                    'journal_id': self.wallet_journal_id.id,
                    'mp_start_date': new_from_date.strftime("%Y/%m/%d %H:%M:%S"),
                    'mp_end_date': new_to_date.strftime("%Y/%m/%d %H:%M:%S")
                })

        if kwargs.get('mode') == 'reconcile_only':
            return bank_statement_raw

        def identify_bank_statement(record_obj, values):
            return record_obj.search([('journal_id', '=', self.wallet_journal_id.id),
                                      ('name', '=', values['name']),
                                      ('mp_account_id', '=', self.id)], limit=1)

        check_existing_records_params = {
            'identifier_method': identify_bank_statement,
            'raw_data': bank_statement_raw,
            'mp_data': bank_statement_raw,
            'multi': isinstance(bank_statement_raw, list)
        }
        check_existing_records = account_bank_statement_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        account_bank_statement_obj.handle_result_check_existing_records(check_existing_records)

        return bank_statement_raw

    def tiktok_auto_reconcile(self, **kwargs):
        _logger = self.env['mp.base']._logger
        if kwargs.get('bank_statement_list', False):
            bank_statement_list = kwargs.get('bank_statement_list')
            bank_statements = self.env['account.bank.statement'].search(
                [('mp_account_id', '=', self.id), ('name', 'in', bank_statement_list)])
            if not bank_statements:
                raise UserError('Bank Statements is not found.')

            for bank_statement in bank_statements:
                if bank_statement.state == 'open':
                    bank_statement.button_post()

            for bank_statement in bank_statements:
                if bank_statement.state == 'posted':
                    # _logger(self.marketplace, 'RECONCILE PROCESS FOR BANK STATEMENTS %s' % (bank_statement.name),
                    #         notify=True,
                    #         notif_sticky=False)

                    # New Method For Reconcile
                    bank_statement.process_bank_statement_reconciliation()
