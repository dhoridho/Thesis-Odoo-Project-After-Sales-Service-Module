# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
# Revised August-2022 PT. HashMicro

from datetime import datetime, timedelta
from email.policy import default
from dateutil.relativedelta import relativedelta
import json
import time

from odoo import api, fields, models

from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.logistic import ShopeeLogistic
from odoo.addons.izi_shopee.objects.utils.shopee.shop import ShopeeShop
from odoo.addons.izi_shopee.objects.utils.shopee.category import ShopeeCategory
from odoo.addons.izi_shopee.objects.utils.shopee.product import ShopeeProduct
from odoo.addons.izi_shopee.objects.utils.shopee.order import ShopeeOrder
from odoo.addons.izi_shopee.objects.utils.shopee.webhook import ShopeeWebhook
from odoo.addons.izi_shopee.objects.utils.shopee.order_return import ShopeeReturn
from odoo.addons.izi_shopee.objects.utils.shopee.promotion import ShopeePromotion
from odoo.addons.izi_shopee.objects.utils.shopee.api import ShopeeAPI
from base64 import b64decode


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    # marketplace = fields.Selection(selection_add=[('shopee', 'Shopee')], ondelete={'shopee': 'cascade'})
    sp_partner_id = fields.Char(string="Partner ID", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_partner_key = fields.Char(string="Partner Key", required_if_marketplace="shopee", states=READONLY_STATES)
    sp_shop_id = fields.Many2one(comodel_name="mp.shopee.shop", string="Shopee Current Shop")
    sp_coins_product_id = fields.Many2one(comodel_name="product.product",
                                          string="Default Shopee Coins Product",
                                          default=lambda self: self._get_default_sp_coins_product_id())
    sp_log_token_ids = fields.One2many(comodel_name='mp.shopee.log.token',
                                       inverse_name='mp_account_id', string='Shopee Log Token')
    sp_is_webhook_order = fields.Boolean(string='Shopee Order Webhook', default=False)
    sp_default_delivery_action = fields.Selection(
        [("pickup", "Request Pickup"), ("dropoff", "Drop Off")], string='Default Delivery Action')
    sp_default_pickup_address = fields.Many2one('mp.shopee.shop.address', string='Default Pickup Address')
    sp_is_live = fields.Boolean(string='Shopee Live Account', default=False)
    sp_log_attribute_ids = fields.One2many(comodel_name='mp.shopee.log.attribute',
                                       inverse_name='mp_account_id', string='Shopee Log Attribute')

    @api.model
    def _get_default_sp_coins_product_id(self):
        sp_coins_product_tmpl = self.env.ref('izi_shopee.product_tmpl_shopee_coins', raise_if_not_found=False)
        if sp_coins_product_tmpl:
            return sp_coins_product_tmpl.product_variant_id.id
        return False

    @api.model
    def shopee_get_account(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if rec.sp_is_live:
            host="live"
        else:
            host="base"
        credentials = {
            'partner_id': int(rec.sp_partner_id),
            'partner_key': rec.sp_partner_key,
            'host': host,
            'mp_id': rec.id,
            'base_url': base_url,
            'access_token': kwargs.get('access_token', rec.access_token),
            'shop_id': kwargs.get('shop_id', int(rec.mp_token_id.sp_shop_id))
        }
        if kwargs.get('code'):
            credentials.update({
                'code': kwargs.get('code', None)
            })
        elif kwargs.get('refresh_token'):
            credentials.update({
                'refresh_token': kwargs.get('refresh_token', rec.mp_token_id.refresh_token),
            })

        sp_account = ShopeeAccount(**credentials)
        return sp_account

    def shopee_authenticate(self):
        self.ensure_one()
        sp_account = self.shopee_get_account()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': sp_account.get_auth_url_v2()
        }

    def shopee_renew_token(self):
        self.ensure_one()
        mp_shopee_log_token = self.env['mp.shopee.log.token']
        current_token = False
        if self.mp_token_ids:
            current_token = self.mp_token_ids.sorted('expired_date', reverse=True)[0]
        if current_token:
            if current_token.refresh_token:
                request_params = {
                    'refresh_token': current_token.refresh_token,
                    'shop_id': current_token.sp_shop_id
                }
                try:
                    token = self.shopee_get_token(**request_params)
                    return token
                except Exception as e:
                    request_params.update({'partner_id': self.sp_partner_id})
                    mp_shopee_log_token.create_log_token(self, e.args[0], request_params, status='fail')
                    raise UserError(str(e.args[0]))

    # @api.multi
    def shopee_get_token(self, **kwargs):
        mp_token_obj = self.env['mp.token']
        mp_shopee_log_token = self.env['mp.shopee.log.token']

        sp_account = self.shopee_get_account(**kwargs)
        shop_id = kwargs.get('shop_id', None)
        raw_token, request_json = sp_account.get_token()
        if shop_id:
            raw_token['shop_id'] = shop_id
        mp_token = mp_token_obj.shopee_create_token(self, raw_token)
        mp_shopee_log_token.create_log_token(self, raw_token, request_json, status='success', mp_token=mp_token)
        time_now = str((datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"))
        auth_message = 'Congratulations, you have been successfully authenticated! from: %s' % (time_now)
        self.write({'state': 'authenticated',
                    'auth_message': auth_message})
        return mp_token

    # @api.multi
    @mp.shopee.capture_error
    def shopee_register_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        webhook_args = {
            'callback_url': base_url + '/api/izi/webhook/sp/order',
            'push_config': {}
        }

        if self.sp_is_webhook_order:
            webhook_args['push_config'].update({
                'order_status': 1,
                'order_tracking_no': 1
            })
        if len(webhook_args.get('push_config')) > 1:
            sp_account = self.shopee_get_account(**params)
            sp_webhook = ShopeeWebhook(sp_account)
            response = sp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                if response.json().get('status') == 'success':
                    notif_msg = "Register webhook is successfully.."
                    self.write({
                        'mp_webhook_state': 'registered'
                    })
                else:
                    notif_msg = "Register webhook is failure.."
                    self.write({
                        'mp_webhook_state': 'no_register'
                    })
            else:
                notif_msg = "Register webhook is failure.."
                self.write({
                    'mp_webhook_state': 'no_register'
                })
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    # @api.multi
    @mp.shopee.capture_error
    def shopee_unregister_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        webhook_args = {
            'callback_url': base_url + '/api/izi/webhook/sp/order',
            'push_config': {}
        }

        if not self.sp_is_webhook_order:
            webhook_args['push_config'].update({
                'order_status': 0,
                'order_tracking_no': 0
            })
        if len(webhook_args.get('push_config')) > 1:
            sp_account = self.shopee_get_account(**params)
            sp_webhook = ShopeeWebhook(sp_account)
            response = sp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                if response.json().get('status') == 'success':
                    notif_msg = "Unregister webhook is successfully.."
                    self.write({
                        'mp_webhook_state': 'no_register'
                    })
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_shop(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_shopee_shop_obj = self.env['mp.shopee.shop'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_shop = ShopeeShop(sp_account, sanitizers=mp_shopee_shop_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        sp_shop_raw = sp_shop.get_shop_info()
        if not sp_shop_raw:
            raise UserError('Shopee shop info is not found.')
        sp_data_raw, sp_data_sanitized = mp_shopee_shop_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_shop_raw)
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': sp_data_raw,
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_shopee_shop_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_shopee_shop_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_logistic(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_shopee_logistic_obj = self.env['mp.shopee.logistic'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_logistic = ShopeeLogistic(sp_account, sanitizers=mp_shopee_logistic_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing logistic from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        sp_data_raw, sp_data_sanitized = sp_logistic.get_logsitic_list()
        check_existing_records_params = {
            'identifier_field': 'logistics_channel_id',
            'raw_data': sp_data_raw['logistics_channel_list'],
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_shopee_logistic_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_shopee_logistic_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_category(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_category_obj = self.env['mp.shopee.category'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_category = ShopeeCategory(sp_account, sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing category from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        sp_data_raw, sp_data_sanitized = sp_category.get_category_list()
        check_existing_records_params = {
            'identifier_field': 'category_id',
            'raw_data': sp_data_raw['category_list'],
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_category_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_category_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        return sp_data_raw, sp_data_sanitized

    def shopee_get_brand_by_category(self, category_id):
        ### new struc
        ### this is used for manual get data from category
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_brand_obj = self.env['mp.shopee.brand'].with_context(mp_account_ctx)
        mp_category_obj = self.env['mp.shopee.category'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_category = ShopeeCategory(sp_account, sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing brand from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        mp_category_obj = self.env['mp.shopee.category'].search([('category_id', '=', category_id)])
        if mp_category_obj:
            mp_brand_raw = []
            for catdata in mp_category_obj:
                if catdata.category_id:
                    sp_brand_data = sp_category.get_brand_list(catdata.category_id)
                    if 'message' in sp_brand_data and sp_brand_data.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                            sp_brand_data.get('error'), sp_brand_data.get('message')))
                    if sp_brand_data:
                        mp_brand_raw.append({
                            'has_brand': True,
                            'category_id': catdata.category_id,
                            'brand_list': sp_brand_data['brand_list']
                        })
                    else:
                        mp_brand_raw.append({
                            'has_brand': False,
                            'category_id': catdata.category_id,
                            'brand_list': []
                        })
                    mp_data_raw = mp_brand_obj.sp_generate_brand_data(mp_brand_raw)
                    sp_data_raws, sp_data_sanitizeds = mp_brand_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)

                    check_existing_records_params = {
                        'identifier_field': 'brand_id',
                        'raw_data': sp_data_raws,
                        'mp_data': sp_data_sanitizeds,
                        'multi': isinstance(sp_data_sanitizeds, list)
                    }
                    check_existing_records = mp_brand_obj.with_context(
                        mp_account_ctx).check_existing_records(**check_existing_records_params)
                    mp_brand_obj.with_context(
                        mp_account_ctx).handle_result_check_existing_records(check_existing_records)
                    self.env.cr.execute(
                        'UPDATE mp_shopee_category SET brand_mapped=true WHERE category_id=%s',
                        (catdata.category_id,)
                    )

    def shopee_get_brand_cron(self):
        ### new struc
        ### this is used for big data from category
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_brand_obj = self.env['mp.shopee.brand'].with_context(mp_account_ctx)
        mp_category_obj = self.env['mp.shopee.category'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_category = ShopeeCategory(sp_account, sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing brand from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        self.env.cr.execute(
            'UPDATE mp_shopee_category SET brand_mapped=true WHERE (has_children = True OR parent_category_id=0) AND (brand_mapped is null or brand_mapped=false)'
        )
        mp_category_obj = self.env['mp.shopee.category'].search(
            [('has_children', '=', False), ('parent_category_id', '!=', 0), ('brand_mapped', '=', False)],
            order="category_id asc", limit=20)
        if mp_category_obj:
            mp_brand_raw = []
            for catdata in mp_category_obj:
                if catdata.category_id:
                    sp_brand_data = sp_category.get_brand_list(catdata.category_id)

                    if sp_brand_data:
                        mp_brand_raw.append({
                            'has_brand': True,
                            'category_id': catdata.category_id,
                            'brand_list': sp_brand_data['brand_list']
                        })
                    else:
                        mp_brand_raw.append({
                            'has_brand': False,
                            'category_id': catdata.category_id,
                            'brand_list': []
                        })
                    mp_data_raw = mp_brand_obj.sp_generate_brand_data(mp_brand_raw)
                    sp_data_raws, sp_data_sanitizeds = mp_brand_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)

                    check_existing_records_params = {
                        'identifier_field': 'brand_id',
                        'raw_data': sp_data_raws,
                        'mp_data': sp_data_sanitizeds,
                        'multi': isinstance(sp_data_sanitizeds, list)
                    }
                    check_existing_records = mp_brand_obj.with_context(
                        mp_account_ctx).check_existing_records(**check_existing_records_params)
                    mp_brand_obj.with_context(
                        mp_account_ctx).handle_result_check_existing_records(check_existing_records)
                    self.env.cr.execute(
                        'UPDATE mp_shopee_category SET brand_mapped=true WHERE category_id=%s',
                        (catdata.category_id,)
                    )


    def shopee_get_brand(self, sp_data_raw):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_brand_obj = self.env['mp.shopee.brand'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        # _notify('info', 'Importing brand from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        mp_data_raw = mp_brand_obj.sp_generate_brand_data(sp_data_raw)
        sp_data_raws, sp_data_sanitizeds = mp_brand_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)

        check_existing_records_params = {
            'identifier_field': 'brand_id',
            'raw_data': sp_data_raws,
            'mp_data': sp_data_sanitizeds,
            'multi': isinstance(sp_data_sanitizeds, list)
        }
        check_existing_records = mp_brand_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_brand_obj.with_context(
            mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_attribute_by_category(self, category_id):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        mp_attribute_obj = self.env['mp.shopee.attribute'].with_context(mp_account_ctx)
        mp_category_obj = self.env['mp.shopee.category'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_category = ShopeeCategory(sp_account, sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing attribute from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        mp_category_obj = self.env['mp.shopee.category'].search([('category_id', '=', category_id)])
        if mp_category_obj:
            mp_attribute_raw = []
            for catdata in mp_category_obj:
                sp_attribute_data = sp_category.get_attribute_list(catdata.category_id)
                if 'message' in sp_attribute_data and sp_attribute_data.get('message') != '':
                    raise UserError('Shopee API error with the code: %s caused by %s' % (
                    sp_attribute_data.get('error'), sp_attribute_data.get('message')))
                if sp_attribute_data:
                    mp_attribute_raw.append({
                        'has_attribute': True,
                        'category_id': catdata.category_id,
                        'attribute_list': sp_attribute_data['attribute_list']
                    })
                else:
                    mp_attribute_raw.append({
                        'has_attribute': False,
                        'category_id': catdata.category_id,
                        'attribute_list': []
                    })

                mp_data_raw = mp_attribute_obj.sp_generate_attribute_data(mp_attribute_raw, mp_account_id)
                sp_data_raws, sp_data_sanitizeds = mp_attribute_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)
                check_existing_records_params = {
                    'identifier_field': 'attribute_id',
                    'raw_data': sp_data_raws,
                    'mp_data': sp_data_sanitizeds,
                    'multi': isinstance(sp_data_sanitizeds, list)
                }
                check_existing_records = mp_attribute_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_attribute_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_attribute_cron(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        mp_attribute_obj = self.env['mp.shopee.attribute'].with_context(mp_account_ctx)
        mp_category_obj = self.env['mp.shopee.category'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_category = ShopeeCategory(sp_account, sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing attribute from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        self.env.cr.execute(
            'UPDATE mp_shopee_category SET attribute_mapped=true WHERE (has_children = True OR parent_category_id=0) AND (attribute_mapped is null or attribute_mapped=false)'
        )
        mp_category_obj = self.env['mp.shopee.category'].search(
            [('has_children', '=', False), ('parent_category_id', '!=', 0), ('attribute_mapped', '=', False)],
            order="category_id asc", limit=20)
        if mp_category_obj:
            mp_category_ids = []
            mp_shopee_log_attribute = self.env['mp.shopee.log.attribute']
            # mp_category_ids.append(catd.category_id for catd in mp_category_obj)
            for catd in mp_category_obj:
                mp_category_ids.append(catd.category_id)
            try:
                for catdata in mp_category_obj:
                    mp_attribute_raw = []
                    sp_attribute_data = sp_category.get_attribute_list(catdata.category_id)
                    if sp_attribute_data:
                        mp_attribute_raw.append({
                            'has_attribute': True,
                            'category_id': catdata.category_id,
                            'attribute_list': sp_attribute_data['attribute_list']
                        })
                    else:
                        mp_attribute_raw.append({
                            'has_attribute': False,
                            'category_id': catdata.category_id,
                            'attribute_list': []
                        })
                # sp_attribute_data = sp_category.get_attribute_list_tree(mp_category_ids)
                # if sp_attribute_data:
                #     for att in sp_attribute_data['list']:
                #         if att.get('attribute_tree'):
                #             mp_attribute_raw.append({
                #                 'has_attribute': True,
                #                 'category_id': att.get('category_id'),
                #                 'attribute_list': att.get('attribute_tree')
                #             })
                #         else:
                #             mp_attribute_raw.append({
                #                 'has_attribute': False,
                #                 'category_id': att.get('category_id'),
                #                 'attribute_list': []
                #             })

                    mp_data_raw = mp_attribute_obj.sp_generate_attribute_data(mp_attribute_raw, mp_account_id)
                    sp_data_raws, sp_data_sanitizeds = mp_attribute_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)
                    check_existing_records_params = {
                        'identifier_field': 'attribute_id',
                        'raw_data': sp_data_raws,
                        'mp_data': sp_data_sanitizeds,
                        'multi': isinstance(sp_data_sanitizeds, list)
                    }
                    check_existing_records = mp_attribute_obj.with_context(
                        mp_account_ctx).check_existing_records(**check_existing_records_params)
                    mp_attribute_obj.with_context(
                        mp_account_ctx).handle_result_check_existing_records(check_existing_records)
                    self.env.cr.execute(
                        'UPDATE mp_shopee_category SET attribute_mapped=true WHERE category_id=%s',
                        (catdata.category_id,)
                    )
                    mp_shopee_log_attribute.create_log_attribute(self, mp_attribute_raw, catdata.category_id, status='success')
            except Exception as e:
                mp_shopee_log_attribute.create_log_attribute(self, e.args[0], mp_category_ids, status='fail')
                raise UserError(str(e.args[0]))

    def shopee_get_attribute(self, sp_data_raw):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        mp_attribute_obj = self.env['mp.shopee.attribute'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        # _notify('info', 'Importing attribute from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        mp_data_raw = mp_attribute_obj.sp_generate_attribute_data(sp_data_raw, mp_account_id)
        sp_data_raws, sp_data_sanitizeds = mp_attribute_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)
        check_existing_records_params = {
            'identifier_field': 'attribute_id',
            'raw_data': sp_data_raws,
            'mp_data': sp_data_sanitizeds,
            'multi': isinstance(sp_data_sanitizeds, list)
        }
        check_existing_records = mp_attribute_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_attribute_obj.with_context(
            mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @api.multi
    def shopee_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.sp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    def shopee_get_address(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_shopee_shop_address_obj = self.env['mp.shopee.shop.address'].with_context(mp_account_ctx)
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_shop_address = ShopeeShop(sp_account)
        # _notify('info', 'Importing logistic from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        sp_data_raw = sp_shop_address.get_shop_address()
        sp_data_raws, sp_data_sanitizeds = [], []
        for address in sp_data_raw['address_list']:
            if 'DEFAULT_ADDRESS' in address['address_type']:
                address.update({
                    'default_address': True
                })
            if 'PICKUP_ADDRESS' in address['address_type']:
                address.update({
                    'pickup_address': True
                })
            if 'RETURN_ADDRESS' in address['address_type']:
                address.update({
                    'return_address': True
                })
            address.update({'shop_id': self.sp_shop_id.id})
        sp_data_raws, sp_data_sanitizeds = mp_shopee_shop_address_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_data_raw['address_list'])

        check_existing_records_params = {
            'identifier_field': 'address_id',
            'raw_data': sp_data_raws,
            'mp_data': sp_data_sanitizeds,
            'multi': isinstance(sp_data_sanitizeds, list)
        }
        check_existing_records = mp_shopee_shop_address_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        mp_shopee_shop_address_obj.with_context(
            mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_category_brand_attribute_manually(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        if kwargs.get('category_id', False):
            category_id = kwargs.get('category_id')
        rec.ensure_one()
        # sp_data_raw, sp_data_sanitized = rec.shopee_get_category()
        rec.shopee_get_brand_by_category(category_id)
        rec.shopee_get_attribute_by_category(category_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def shopee_get_category_attribute(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        # sp_data_raw, sp_data_sanitized = rec.shopee_get_category()
        rec.shopee_get_brand_cron()
        rec.shopee_get_attribute_cron()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    # @api.multi
    def shopee_get_dependencies(self):
        self.ensure_one()
        self.shopee_get_shop()
        self.shopee_get_logistic()
        self.shopee_get_active_logistics()
        self.shopee_get_address()
        sp_data_raw, sp_data_sanitized = self.shopee_get_category()
        # self.shopee_get_brand(sp_data_raw)
        # self.shopee_get_attribute(sp_data_raw)
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        cron_name = 'IZI Shopee Attribute Scheduler %s' % (str(mp_account_id))
        cron_order = self.env['ir.cron'].sudo().search([('name', '=', cron_name), ('active', '=', False)])
        delta_var = 'seconds'
        interval = 10
        next_call = datetime.now() + eval(f'timedelta({delta_var}={interval})')
        if cron_order:
            cron_order.sudo().write({
                'nextcall': next_call,
                'active': True
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_mp_product(self, **kw):
        mp_product_obj = self.env['mp.product']
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        self.ensure_one()
        params = {}
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**params)
        sp_product = ShopeeProduct(sp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing product from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

        if kw.get('product_ids'):
            # product_ids = list(map(str, kw.get('product_ids')))
            sp_data_raw, sp_data_sanitized = sp_product.get_product_info(product_id=kw.get('product_ids'))
            # existing_mp_products = mp_product_obj.search(
            #     [('mp_account_id', '=', self.id), ('mp_external_id', 'in', product_ids)])
        else:
            sp_data_raw, sp_data_sanitized = sp_product.get_product_list(limit=mp_account_ctx.get('product_limit'))
            # existing_mp_products = mp_product_obj.search([('mp_account_id', '=', self.id)])
            if not sp_data_raw:
                raise UserError('Products not found')
        # sp_product_exid = list(map(lambda x: str(x['item_id']), sp_data_raw))
        # mp_product_need_to_archive = []
        # for mp_product in existing_mp_products:
        #     if mp_product.mp_external_id not in sp_product_exid:
        #         mp_product_need_to_archive.append(mp_product.mp_external_id)

        check_existing_records_params = {
            'identifier_field': 'sp_product_id',
            'raw_data': sp_data_raw,
            'mp_data': sp_data_sanitized,
            'multi': isinstance(sp_data_sanitized, list)
        }
        check_existing_records = mp_product_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        if check_existing_records['need_update_records']:
            mp_product_obj.with_context({'mp_account_id': self.id}).update_records(
                check_existing_records['need_update_records'])

        if check_existing_records['need_create_records']:
            sp_data_raw, sp_data_sanitized = mp_product_obj.with_context(mp_account_ctx)._prepare_create_records(
                check_existing_records['need_create_records'])
            mp_product_obj.with_context(mp_account_ctx).create_records(sp_data_raw, sp_data_sanitized,
                                                                       isinstance(sp_data_sanitized, list))
        if check_existing_records['need_skip_records']:
            mp_product_obj.with_context(mp_account_ctx).log_skip(
                self.marketplace, check_existing_records['need_skip_records'])

        ### create or update mp_stock for product
        mp_stock_obj = self.env['mp.stock']
        mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=sp_data_raw)


        # # archive mp_product if doesnt exists in marketplace
        # mp_products_archive = existing_mp_products.filtered(lambda r: r.mp_external_id in mp_product_need_to_archive)
        # for product in mp_products_archive:
        #     for variant in product.mp_product_variant_ids:
        #         variant.active = False
        #     product.active = False

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_mp_product_variant(self, **kw):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        if kw.get('product_ids'):
            product_ids = list(map(str, kw.get('product_ids')))
            mp_products = mp_product_obj.search(
                [('mp_external_id', 'in', product_ids),
                 ('mp_account_id', '=', self.id),
                 ('sp_has_variant', '=', True)])
        else:
            mp_products = mp_product_obj.search([('sp_has_variant', '=', True), ('mp_account_id', '=', self.id)])

        if mp_products:
            for mp_product in mp_products:
                variant_need_to_remove = []
                mp_product_raw = json.loads(mp_product.raw, strict=False)
                mp_product_variant_raw = mp_product_variant_obj.sp_generate_variant_data(mp_product_raw)
                mp_product.write({
                    'sp_variant_line': json.dumps(mp_product_variant_raw[0]['variant_line'])
                })
                # mp_variant_exid_list = [variant_id['sp_variant_id'] for variant_id in mp_product_variant_raw]
                sp_data_raw, sp_data_sanitized = mp_product_variant_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_product_variant_raw)

                check_existing_records_params = {
                    'identifier_field': 'sp_variant_id',
                    'raw_data': sp_data_raw,
                    'mp_data': sp_data_sanitized,
                    'multi': isinstance(sp_data_sanitized, list)
                }
                check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
                    **check_existing_records_params)
                mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                    check_existing_records)

                ### create or update mp_stock for variant
                mp_stock_obj = self.env['mp.stock']
                mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=mp_product_variant_raw, map_type='variant')

                # for variant_obj in mp_product.mp_product_variant_ids:
                #     if int(variant_obj.sp_variant_id) not in mp_variant_exid_list:
                #         variant_need_to_remove.append(variant_obj.sp_variant_id)

                # mp_product.mp_product_variant_ids.filtered(lambda r: r.sp_variant_id in variant_need_to_remove).write({
                #     'active': False
                # })

        # clean variant
        # mp_products = mp_product_obj.search([('mp_product_variant_ids', '!=', False),
        #                                     ('sp_has_variant', '=', False),
        #                                     ('mp_account_id', '=', self.id)])
        # for product in mp_products:
        #     for variant in product.mp_product_variant_ids:
        #         variant.active = False

    # @api.multi
    def shopee_get_products(self, **kw):
        self.ensure_one()
        self.shopee_get_mp_product(**kw)
        self.shopee_get_mp_product_variant(**kw)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    # @api.multi
    @mp.shopee.capture_error
    def shopee_get_sale_order(self, time_mode='update_time', **kwargs):
        mp_account_ctx = self.generate_context()
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))

        # if kwargs.get('mp_account_id', False):
        #     rec = self.browse(kwargs.get('mp_account_id'))
        # else:
        #     rec = self
        if kwargs.get('force_update'):
            mp_account_ctx.update({'force_update': kwargs.get('force_update')})
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        account_params = {}
        order_params = {}
        if rec.mp_token_id.state == 'valid':
            account_params = {'access_token': rec.mp_token_id.name}
        sp_account = rec.shopee_get_account(**account_params)
        sp_order_v2 = ShopeeOrder(sp_account, sanitizers=order_obj.get_sanitizers(rec.marketplace))
        # sp_order_v1 = ShopeeOrder(sp_account, api_version="v1")
        # _notify('info', 'Importing order from {} is started... Please wait!'.format(rec.marketplace.upper()),
        #         notif_sticky=False)

        skipped = 0
        force_update_ids = []
        sp_order_list = []
        sp_order_raws = False
        sp_order_sanitizeds = False
        sp_orders_by_mpexid = {}
        sp_orders = order_obj.search([('mp_account_id', '=', rec.id), ('sp_order_status', 'not in', ['COMPLETED'])])
        for sp_order in sp_orders:
            sp_orders_by_mpexid[sp_order.mp_invoice_number] = sp_order

        def get_order_income(sp_data_raws):
            sp_order_raws, sp_order_sanitizeds = [], []
            for index, data in enumerate(sp_data_raws):
                sp_order_invoice = data.get('order_sn')
                notif_msg = "(%s/%d) Getting order detail of %s... Please wait!" % (
                    str(index + 1), len(sp_data_raws), sp_order_invoice
                )
                # _logger(rec.marketplace, notif_msg, notify=True, notif_sticky=False)
                # get_income
                # income_data = sp_order_v1.get_income(**{'order_sn': data['order_sn']})
                ### order income v1 sudah tidak ada dalam list API dari shopee
                ### sekarang diganti menjadi v2 payment -> get_escrow_detail
                income_data = sp_order_v2.get_income(**{'order_sn': data['order_sn']})
                data.update({'order_income': income_data.get('order_income', False), 'branch_id': rec.branch_id.id})
                sp_order_data_raw, sp_order_data_sanitized = order_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
                sp_order_raws.append(sp_order_data_raw)
                sp_order_sanitizeds.append(sp_order_data_sanitized)
            return sp_order_raws, sp_order_sanitizeds

        if kwargs.get('params') == 'by_date_range':

            order_params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'limit': mp_account_ctx.get('order_limit'),
                'time_mode': time_mode,
            })
            sp_order_list = sp_order_v2.get_order_list(**order_params)
            order_list = []
            sp_data_raws = []
            if sp_order_list:
                for sp_data_order in sp_order_list:
                    sp_order_invoice = sp_data_order.get('order_sn')
                    if sp_order_invoice in sp_orders_by_mpexid:
                        existing_order = sp_orders_by_mpexid[sp_order_invoice]
                        mp_status_changed = existing_order.sp_order_status != str(sp_data_order['order_status'])
                    else:
                        existing_order = False
                        mp_status_changed = False
                    no_existing_order = not existing_order
                    if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                        if sp_data_order['order_status'] == 'CANCELLED' and no_existing_order:
                            if not rec.get_cancelled_orders:
                                skipped += 1
                                continue
                        if existing_order and mp_account_ctx.get('force_update'):
                            force_update_ids.append(existing_order.id)
                        if not rec.get_unpaid_orders:
                            if sp_data_order['order_status'] != 'UNPAID':
                                order_list.append({'order_sn': sp_order_invoice})
                        else:
                            order_list.append({'order_sn': sp_order_invoice})
                    else:
                        skipped += 1

            if order_list:
                sp_data_raws = sp_order_v2.get_order_detail(sp_data=order_list)
                sp_order_raws, sp_order_sanitizeds = get_order_income(sp_data_raws)

            # _logger(rec.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
            #         len(order_list), len(sp_data_raws)
            #         ), notify=True, notif_sticky=False)

        elif kwargs.get('params') == 'by_mp_invoice_number':
            sp_process_order = []
            shopee_invoice_number = kwargs.get('mp_invoice_number')
            if type(shopee_invoice_number) == str:
                shopee_invoice_number = [inv for inv in shopee_invoice_number.split(',')]
            sp_data_raws = sp_order_v2.get_order_detail(**{'order_ids': shopee_invoice_number})
            if sp_order_raws:
                for order in sp_data_raws:
                    if order['order_sn'] in sp_orders_by_mpexid:
                        existing_order = sp_orders_by_mpexid[order['order_sn']]
                        mp_status_changed = existing_order.sp_order_status != order['order_status']
                    else:
                        existing_order = False
                        mp_status_changed = False
                    no_existing_order = not existing_order
                    if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                        if order['order_status'] == 'CANCELLED' and no_existing_order:
                            if not rec.get_cancelled_orders:
                                skipped += 1
                                continue
                        elif order['order_status'] == 'UNPAID' and no_existing_order:
                            if not rec.get_unpaid_orders:
                                skipped += 1
                                continue

                        sp_process_order.append(order)

                        if existing_order and mp_account_ctx.get('force_update'):
                            force_update_ids.append(existing_order.id)
                    else:
                        skipped += 1

            if sp_process_order:
                sp_order_raws, sp_order_sanitizeds = get_order_income(sp_process_order)

            # _logger(rec.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
            #         len(sp_process_order), len(sp_data_raws)
            #         ), notify=True, notif_sticky=False)

        if force_update_ids:
            order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                'force_update_ids': force_update_ids
            }))

        if sp_order_raws and sp_order_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_order_id',
                'raw_data': sp_order_raws,
                'mp_data': sp_order_sanitizeds,
                'multi': isinstance(sp_order_sanitizeds, list)
            }
            check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        # else:
        #     _logger(rec.marketplace, 'There is no update, skipped %s order(s)!' % skipped, notify=True,
        #             notif_sticky=False)

    # @api.multi
    def shopee_get_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_mode = kwargs.get('time_mode', 'update_time')
        if 'time_mode' in kwargs:
            kwargs.pop('time_mode')
        # self.shopee_get_sale_order(time_range='create_time', **kwargs)
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
        rec.shopee_get_sale_order(time_mode=time_mode, **kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @mp.shopee.capture_error
    def shopee_get_saldo_history(self, **kwargs):
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
                'name': 'Shopee Saldo: %s' % ((from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                'date': (from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                'journal_id': self.wallet_journal_id.id,
                'mp_start_date': from_date_str,
                'mp_end_date': to_date_str
            })
        else:
            for index in range(0, total_days):
                # new_from_date = from_date + relativedelta(days=index)
                # new_to_date = from_date + relativedelta(days=index, hours=24)
                #### -7 agar data yang didapatkan sesuai dengan display dari shopee
                new_from_date = from_date + relativedelta(days=index, hours=-7)
                new_to_date = from_date + relativedelta(days=index, hours=17)
                if new_to_date.day == to_date.day:
                    new_to_date = to_date
                bank_statement_raw.append({
                    'name': 'Shopee Saldo: %s' % ((new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
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

    def shopee_auto_reconcile(self, **kwargs):
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

    def shopee_get_orders_wallet(self, **kwargs):
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
        bank_statement = rec.shopee_get_saldo_history(**kwargs)
        if kwargs.get('mode') in ['reconcile_only', 'both']:
            bank_statement_list = [data['name'] for data in bank_statement]
            auto_rec_param = {'bank_statement_list': bank_statement_list}
            rec.shopee_auto_reconcile(**auto_rec_param)
        mp_account_ctx = rec.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        cron_name = 'IZI Shopee Wallet Scheduler %s' % (str(mp_account_id))
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

    def shopee_set_product(self, **kw):
        self.ensure_one()
        sp_account = self.shopee_get_account()

        api = ShopeeAPI(sp_account)
        mp_product_ids = []
        if kw.get('mode') == 'price_only':
            for data in kw.get('data', []):
                try:
                    prepared_request = api.build_request(
                        'set_product_price',
                        sp_account.partner_id,
                        sp_account.partner_key,
                        sp_account.shop_id,
                        sp_account.host,
                        sp_account.access_token)
                    if data['product_obj']._name == 'mp.product':
                        prepared_request = {**prepared_request, **{
                            'json': {
                                'item_id': int(data['product_obj'].mp_external_id),
                                'price_list': [{
                                    'model_id': 0,
                                    'original_price': data['price']
                                }]
                            }
                        }}
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        prepared_request = {**prepared_request, **{
                            'json': {
                                'item_id': int(data['product_obj'].mp_product_id.mp_external_id),
                                'price_list': [{
                                    'model_id': int(data['product_obj'].mp_external_id),
                                    'original_price': data['price']
                                }]
                            }
                        }}
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                    process_response = api.process_response('set_product_price', api.request(**prepared_request))
                    if 'message' in process_response and process_response.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                        process_response.get('error'), process_response.get('message')))
                    # self.env['mp.base']._logger(self.marketplace, 'Product %s updated' %
                    #                             (data['product_obj'].name), notify=True, notif_sticky=False)
                except Exception as e:
                    self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'stock_only':
            for data in kw.get('data', []):
                try:
                    prepared_request = api.build_request(
                        'set_product_stock',
                        sp_account.partner_id,
                        sp_account.partner_key,
                        sp_account.shop_id,
                        sp_account.host,
                        sp_account.access_token)
                    if data['product_obj']._name == 'mp.product':
                        prepared_request = {**prepared_request, **{
                            'json': {
                                'item_id': int(data['product_obj'].mp_external_id),
                                'stock_list': [{
                                    'model_id': 0,
                                    # 'normal_stock': data['stock']
                                    'seller_stock': [{
                                        'stock': data['stock']
                                    }]
                                }]
                            }
                        }}
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        prepared_request = {**prepared_request, **{
                            'json': {
                                'item_id': int(data['product_obj'].mp_product_id.mp_external_id),
                                'stock_list': [{
                                    'model_id': int(data['product_obj'].mp_external_id),
                                    # 'normal_stock': data['stock']
                                    'seller_stock': [{
                                        'stock': data['stock']
                                    }]
                                }]
                            }
                        }}
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                    process_response = api.process_response('set_product_stock', api.request(**prepared_request))
                    if 'message' in process_response and process_response.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                        process_response.get('error'), process_response.get('message')))
                    # self.env['mp.base']._logger(self.marketplace, 'Product %s updated' %
                    #                             (data['product_obj'].name), notify=True, notif_sticky=False)
                except Exception as e:
                    self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'activation':
            try:
                prepared_request = api.build_request(
                    'set_product_unlist',
                    sp_account.partner_id,
                    sp_account.partner_key,
                    sp_account.shop_id,
                    sp_account.host,
                    sp_account.access_token)
                item_list = []
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        item_list.append({
                            "item_id": int(data['product_obj'].mp_external_id),
                            "unlist": not data['activate']
                        })
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                if item_list:
                    prepared_request = {**prepared_request, **{
                        'json': {
                            'item_list': item_list
                        }
                    }}
                    process_response = api.process_response('set_product_stock', api.request(**prepared_request))
                    if 'message' in process_response and process_response.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                        process_response.get('error'), process_response.get('message')))
                    # self.env['mp.base']._logger(self.marketplace, 'Product(s) updated', notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'detail':
            try:
                prepared_request = api.build_request(
                    'set_product_detail',
                    sp_account.partner_id,
                    sp_account.partner_key,
                    sp_account.shop_id,
                    sp_account.host,
                    sp_account.access_token, **{
                        'params': {
                            'item_id': int(kw['data'].mp_product_id.mp_external_id),
                        }
                    })
#                 preprocessed_request = {
#                     'wholesale': [{
#                         'min_count': 1,
#                         'max_count': 1000,
#                         'unit_price': kw['data'].mp_product_id.list_price,
#                     }]
#                 }
                preprocessed_request = {}
                if kw['data'].wholesale_ids:
                    preprocessed_request['wholesale'] = []
                    wholesale_len = len(kw['data'].wholesale_ids)
                    for wsl_idx in range(0, wholesale_len):
                        wsl_data = kw['data'].wholesale_ids[wsl_idx]
                        max_count = wsl_data.min_qty * 100
                        if wsl_idx < (wholesale_len - 1):
                            max_count = kw['data'].wholesale_ids[wsl_idx + 1].min_qty - 1
                        preprocessed_request['wholesale'].append({
                            'min_count': wsl_data.min_qty,
                            'max_count': max_count,
                            'unit_price': wsl_data.price,
                        })
                if kw['data'].image_ids:
                    image_id_list = []
                    for image_id in kw['data'].image_ids:
                        image_prepared_request = api.build_request(
                            'set_product_image',
                            sp_account.partner_id,
                            sp_account.partner_key,
                            sp_account.shop_id,
                            sp_account.host,
                            sp_account.access_token, **{
                                'data': {
                                    'scene': 'normal',
                                },
                                'files': {
                                    'image': ('image.png', b64decode(image_id.image), 'image/png')
                                }
                            })
                        image_prepared_request['headers'] = None
                        image_process_response = api.process_response(
                            'set_product_image', api.request(**image_prepared_request))
                        if image_process_response.get('image_info', {}).get('image_id'):
                            image_id_list.append(image_process_response['image_info']['image_id'])
                        # else:
                        #     self.env['mp.base']._logger(self.marketplace, 'Product image %s failed to update' % (
                        #         kw['data'].name), notify=True, notif_sticky=False)
                    if image_id_list:
                        preprocessed_request['image'] = {'image_id_list': image_id_list}
                prepared_request = {**prepared_request, **{
                    'json': {
                        'item_id': int(kw['data'].mp_product_id.mp_external_id),
                        'item_name': kw['data'].name,
                        'description': kw['data'].description,
                        'item_sku': kw['data'].sku,
                        'condition': kw['data'].condition,
                        'weight': kw['data'].weight,
                        'dimension': {
                            'package_height': int(kw['data'].height),
                            'package_length': int(kw['data'].width),
                            'package_width': int(kw['data'].length),
                        },
                        **preprocessed_request,
                    }
                }}
                mp_product_ids = kw['data'].mp_product_id.mapped('mp_external_id')
                process_response = api.process_response('set_product_detail', api.request(**prepared_request))
                # self.env['mp.base']._logger(self.marketplace, 'Product %s updated' %
                #                             (kw['data'].name), notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        self.shopee_get_products(**{'product_ids': mp_product_ids})

    def shopee_process_webhook_orders(self, **kwargs):

        if not self.exists():
            if kwargs.get('id', False):
                rec = self.browse(kwargs.get('id'))
        else:
            rec = self
        # self.env['mp.base']._logger(rec.marketplace, 'START PROCESSING SHOPEE WEBHOOK ORDER %s' %
        #                             (str(rec.id)), notify=False, notif_sticky=False)
        rec.ensure_one()
        limit = 100
        webhook_order_obj = self.env['mp.webhook.order']
        order_not_process = webhook_order_obj.search(
            [('mp_account_id', '=', rec.id),
             ('is_process', '=', False),
             ('sp_order_status', '=', 'READY_TO_SHIP')], order='write_date', limit=limit)
        if order_not_process:
            order_not_process.is_process = True

        limit = limit+(100-len(order_not_process))
        order_has_process = webhook_order_obj.search(
            [('mp_account_id', '=', rec.id),
             ('is_process', '=', False),
             ('sp_order_status', 'not in', ['UNPAID', 'READY_TO_SHIP'])], order='write_date', limit=limit)
        if order_has_process:
            order_has_process.is_process = True

        mp_invoice_number_in_process = [order.mp_invoice_number for order in order_not_process]
        mp_invoice_number_has_process = [order.mp_invoice_number for order in order_has_process]

        so_in_process = rec.shopee_get_sale_order(**{
            'mp_invoice_number': mp_invoice_number_in_process,
            'params': 'by_mp_invoice_number'})
        so_has_process = rec.shopee_get_sale_order(**{
            'mp_invoice_number': mp_invoice_number_has_process,
            'params': 'by_mp_invoice_number'})
        # self.env['mp.base']._logger(rec.marketplace, 'END PROCESSING SHOPEE WEBHOOK ORDER %s' %
        #                             (str(rec.id)), notify=False, notif_sticky=False)

    @mp.shopee.capture_error
    def shopee_get_order_return(self, **kwargs):
        mp_account_ctx = self.generate_context()
        if kwargs.get('force_update'):
            mp_account_ctx.update({'force_update': kwargs.get('force_update')})
        mp_return_obj = self.env['mp.return'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        account_params = {}
        return_params = {}

        def _get_current_return_obj(mp_account_id):
            sp_return_by_mpexid = {}
            sp_returns = mp_return_obj.search([('mp_account_id', '=', mp_account_id)])
            for sp_return in sp_returns:
                sp_return_by_mpexid[sp_return.mp_external_id] = sp_return
            return sp_return_by_mpexid

        if self.mp_token_id.state == 'valid':
            account_params = {'access_token': self.mp_token_id.name}
            sp_account = self.shopee_get_account(**account_params)
            sp_return_v2 = ShopeeReturn(sp_account)
            # _notify('info', 'Importing order return from {} is started... Please wait!'.format(self.marketplace.upper()),
            #         notif_sticky=False)
            skipped = 0
            sp_order_raws, sp_order_sanitizeds = [], []
            return_data_process = []
            if kwargs.get('params') == 'by_date_range':
                return_params.update({
                    'from_date': kwargs.get('from_date'),
                    'to_date': kwargs.get('to_date'),
                    'limit': mp_account_ctx.get('order_limit'),
                })
                sp_order_return_list = sp_return_v2.get_return_list(**return_params)
                if sp_order_return_list:
                    sp_return_by_mpexid = _get_current_return_obj(self.id)
                    for return_data in sp_order_return_list:
                        return_sn = str(return_data.get('return_sn'))
                        if return_sn not in sp_return_by_mpexid:
                            if return_data.get('status') not in ['CANCELLED', 'CLOSED']:
                                return_data_process.append(return_data)
                            else:
                                skipped += 1
                        else:
                            current_return = sp_return_by_mpexid[return_sn]
                            # if mp_account_ctx.get('force_update'):
                            #     return_data_process.append(return_data)
                            if current_return.sp_return_status != return_data.get('status'):
                                return_data_process.append(return_data)
                            else:
                                skipped += 1

                    if return_data_process:
                        sp_order_return_detail = sp_return_v2.get_return_detail(**{'return_list': return_data_process})
                        sp_order_raws, sp_order_sanitizeds = mp_return_obj.with_context(
                            mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_order_return_detail)

            elif kwargs.get('params') == 'by_mp_return_number':
                shopee_return_number = kwargs.get('mp_return_number')
                if type(shopee_return_number) == str:
                    shopee_return_number = [{'return_sn': shopee_return_number}]
                sp_order_return_detail = sp_return_v2.get_return_detail(**{'return_list': shopee_return_number})
                sp_order_raws, sp_order_sanitizeds = mp_return_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_order_return_detail)

            if sp_order_raws and sp_order_sanitizeds:
                check_existing_records_params = {
                    'identifier_field': 'sp_return_sn',
                    'raw_data': sp_order_raws,
                    'mp_data': sp_order_sanitizeds,
                    'multi': isinstance(sp_order_sanitizeds, list)
                }
                check_existing_records = mp_return_obj.with_context(mp_account_ctx).check_existing_records(
                    **check_existing_records_params)
                mp_return_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                    check_existing_records)
            # else:
            #     _logger(self.marketplace, 'There is no update, skipped %s return(s)!' % skipped, notify=True,
            #             notif_sticky=False)

    def shopee_get_return(self, **kwargs):
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
            elif time_range == 'last_7_days':
                from_time = datetime.now() - timedelta(days=7)
                to_time = datetime.now()
            elif time_range == 'last_14_days':
                from_time = datetime.now() - timedelta(days=14)
                to_time = datetime.now()
            kwargs.update({
                'from_date': from_time,
                'to_date': to_time
            })
        rec.shopee_get_order_return(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def shopee_auto_ship_orders(self, **kwargs):
        if not self.exists():
            if kwargs.get('id', False):
                rec = self.browse(kwargs.get('id'))
        else:
            rec = self
        rec.ensure_one()
        domain = [('mp_account_id', '=', rec.id),
                  ('mp_order_status', '=', 'in_process'),
                  ('mp_awb_number', '=', False)]
        if kwargs.get('order_list', False):
            sp_order_list = kwargs.get('order_list')
            domain.append(('mp_invoice_number', 'in', sp_order_list))

        _logger = self.env['mp.base']._logger
        so_obj = self.env['sale.order']
        pickup_order = []
        dropoff_order = []
        order_list = []

        # checking cutoff time
        now = datetime.now()
        tz_now = now.astimezone(kwargs.get('tz'))
        checking_cutoff = self.checking_cutoff_time(now=now, tz_now=tz_now)
        if checking_cutoff:
            # if checking cut off is true doesnt process auto ship
            return True

        # fetch order
        sale_orders = so_obj.search(domain=domain, order='write_date', limit=100)
        # _logger(self.marketplace, '[AUTO SHIP] Fetching %s Sale Orders' %
        #         (str(len(sale_orders))), notify=False, notif_sticky=False)

        for order in sale_orders:
            if order.mp_delivery_type == 'both':
                if self.sp_default_delivery_action == 'pickup':
                    pickup_order.append(order.mp_external_id)
                else:
                    dropoff_order.append(order.mp_external_id)
            elif order.mp_delivery_type == 'drop off':
                dropoff_order.ppaned(order.mp_external_id)
            elif order.mp_delivery_type == 'pickup':
                pickup_order.append(order.mp_external_id)

        # processing pickup_order
        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
            sp_account = self.shopee_get_account(**params)
            sp_order_v2 = ShopeeOrder(sp_account)
            sp_order_v1 = ShopeeOrder(sp_account, api_version="v1")
            if pickup_order:
                # _logger(self.marketplace, '[AUTO SHIP] Processing %s Sale Orders for Pickup' %
                #         (str(len(pickup_order))), notify=False, notif_sticky=False)
                action_params = {
                    'order_sn': pickup_order[0],
                }
                shipping_paramater = sp_order_v2.get_shipping_parameter(**action_params)
                address_list = shipping_paramater['pickup']['address_list']
                address_by_exid = {}
                for address in address_list:
                    address_by_exid[address['address_id']] = address['time_slot_list']

                pickup_time_id = False
                default_pick_time = False
                if self.sp_default_pickup_address:
                    address_id = int(self.sp_default_pickup_address.mp_external_id)
                    if address_id in address_by_exid:
                        default_address_time = address_by_exid[address_id]
                        today = datetime.today().day
                        for index, time in enumerate(default_address_time):
                            if datetime.fromtimestamp(time['date']).day == today:
                                pickup_time_id = time['pickup_time_id']
                                default_pick_time = default_address_time[index]
                                break

                if pickup_time_id:
                    for index, ordersn in enumerate(pickup_order):
                        # _logger(self.marketplace, '[AUTO SHIP] Processing %s/%s Sale Orders for Pickup' %
                        #         (str(index+1), str(len(pickup_order))), notify=False, notif_sticky=False)
                        payload = {
                            'order_sn': ordersn,
                            'pickup': {
                                "tracking_no": "",
                                "address_id": address_id,
                                "pickup_time_id": pickup_time_id
                            }
                        }
                        response = sp_order_v2.action_ship_order(**payload)
                        if response == 'success':
                            order_list.append(ordersn)

                    # kwargs = {
                    #     'order_list': [dict(**dict([('order_sn', inv)])) for inv in pickup_order],
                    #     'pickup': {
                    #         "tracking_no": "",
                    #         "address_id": address_id,
                    #         "pickup_time_id": pickup_time_id
                    #     }
                    # }
                    # response = sp_order_v2.action_batch_ship_order(**kwargs)
                    # if 'result_list' in response and response['result_list']:
                    #     success_order_list = [order_data['order_sn'] for order_data in response['result_list']]
                    #     order_list.extend(success_order_list)

            if dropoff_order:
                # For batch ship order
                # kwargs = {
                #     'order_list': [dict(**dict([('ordersn', inv)])) for inv in dropoff_order],
                #     'dropoff': {
                #         "tracking_no": "",
                #         "branch_id": 0,
                #         "sender_real_name": ""
                #     }
                # }
                # response = sp_order_v1.action_batch_ship_order(**kwargs)
                # if 'result_list' in response and response['result_list']:
                #     success_order_list = [order_data['order_sn'] for order_data in response['result_list']]
                #     order_list.extend(success_order_list)
                for index, ordersn in enumerate(dropoff_order):
                    # _logger(self.marketplace, '[AUTO SHIP] Processing %s/%s Sale Orders for Dropoff' %
                    #         (str(index+1), str(len(dropoff_order))), notify=False, notif_sticky=False)
                    payload = {
                        'order_sn': ordersn,
                        'dropoff': {
                            "tracking_no": "",
                            "branch_id": 0,
                            "sender_real_name": ""
                        }
                    }
                    response = sp_order_v2.action_ship_order(**payload)
                    if response == 'success':
                        order_list.append(ordersn)

            if order_list:
                refetch_order = rec.shopee_get_sale_order(**{
                    'mp_invoice_number': order_list,
                    'params': 'by_mp_invoice_number'})

    def shopee_get_webhook_orders(self, **kwargs):
        mp_webhook_order_obj = self.env['mp.webhook.order'].sudo()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        account_params = {}
        order_params = {}
        if self.mp_token_id.state == 'valid':
            account_params = {'access_token': self.mp_token_id.name}
        sp_account = self.shopee_get_account(**account_params)
        sp_order_v2 = ShopeeOrder(sp_account)
        if kwargs.get('params') == 'by_date_range':
            order_params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'limit': mp_account_ctx.get('order_limit'),
                'time_mode': kwargs.get('time_mode'),
            })
            sp_order_list = sp_order_v2.get_order_list(**order_params)
            sp_data_raws = sp_order_v2.get_order_detail(sp_data=sp_order_list)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            shopee_invoice_number = kwargs.get('mp_invoice_number')
            if type(shopee_invoice_number) == str:
                shopee_invoice_number = [inv for inv in shopee_invoice_number.split(',')]
            order_params.update({
                'order_ids': shopee_invoice_number,
            })
            sp_data_raws = sp_order_v2.get_order_detail(**order_params)

        sp_orders_by_mpexid = {}
        sp_orders = mp_webhook_order_obj.search([('mp_account_id', '=', self.id)])
        for order in sp_orders:
            sp_orders_by_mpexid[order.mp_invoice_number] = order

        index = 0
        for sp_order in sp_data_raws:
            index = index + 1
            # _logger(self.marketplace, 'Processing order %s from %s of total orders imported!' % (
            #     str(index), len(sp_data_raws)
            # ), notify=True, notif_sticky=False)
            mp_invoice_number = sp_order.get('order_sn')
            # Create or Write Webhook Order
            mp_existing_order = sp_orders_by_mpexid[mp_invoice_number] if mp_invoice_number in sp_orders_by_mpexid else False
            rec_values = {
                'mp_invoice_number': mp_invoice_number,
                'sp_order_id': sp_order.get('order_sn'),
                'mp_account_id': self.id,
                'order_update_time': datetime.fromtimestamp(
                    time.mktime(time.gmtime(sp_order.get('update_time'))))
                .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'order_create_time': datetime.fromtimestamp(
                    time.mktime(time.gmtime(sp_order.get('create_time'))))
                .strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'sp_order_status': sp_order.get('order_status'),
                'raw': json.dumps(sp_order, indent=4),
            }
            if sp_order.get('shipping_document_info', False):
                rec_values.update({
                    'mp_awb_number': sp_order.get('shipping_document_info').get('tracking_number')
                })
            if mp_existing_order:
                # _logger(self.marketplace, 'Updating Order %s ' %
                #         (mp_invoice_number), notify=False, notif_sticky=False)
                mp_existing_order.write(rec_values)
            else:
                # _logger(self.marketplace, 'Creating Order %s ' %
                #         (mp_invoice_number), notify=False, notif_sticky=False)
                mp_webhook_order_obj.create(rec_values)

    def shopee_get_discount(self, **kw):
        _logger = self.env['mp.base']._logger
        sp_promotion = kw.get('sp_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        mp_account_ctx.update({
            'force_update': True
        })
        mp_promotion_obj = self.env['mp.promotion.program']
        sp_promotion_by_mpexid = kw.get('sp_promotion_by_mpexid')

        sp_discount_raws, sp_discount_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': ['upcoming', 'ongoing']  # Available value: upcoming/ongoing/expired/all.
            }
            sp_discount_list = sp_promotion.get_discount_list(**params)
            if 'message' in sp_discount_list and sp_discount_list.get('message') != '':
                raise UserError('Shopee API error with the code: %s caused by %s' % (sp_discount_list.get('error'), sp_discount_list.get('message')))
            if sp_discount_list:
                for index, sp_data_discount in enumerate(sp_discount_list):
                    notif_msg = "(%s/%d) Getting discount detail of %s... Please wait!" % (
                        str(index + 1), len(sp_discount_list), sp_data_discount.get('discount_id')
                    )
                    # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    raw_data_detail = sp_promotion.get_discount(discount_id=sp_data_discount.get('discount_id'))
                    item_list = []
                    if 'item_list' in raw_data_detail:
                        item_list = raw_data_detail['item_list']
                    raw_data_detail.update({
                        # mapping base info promotion
                        'base_info': {
                            'type': 'discount',
                            'name': raw_data_detail['discount_name'],
                            'status': raw_data_detail['status'],
                            'start_time': raw_data_detail['start_time'],
                            'end_time': raw_data_detail['end_time'],
                            'promotion_id': raw_data_detail['discount_id']
                        },
                        # mapping spesific type promotion fields
                        'discount': {
                            'item_list': item_list
                        },
                        'voucher': {},
                        'bundle': {},
                        'addon': {}
                    })

                    # cleaning key after mapping
                    if 'item_list' in raw_data_detail:
                        raw_data_detail.pop('item_list')
                    raw_data_detail.pop('more')

                    sp_discount_data_raw, sp_discount_data_sanitized = mp_promotion_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
                    sp_discount_raws.append(sp_discount_data_raw)
                    sp_discount_sanitizeds.append(sp_discount_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting discount detail of %s... Please wait!" % (
                mp_promotion_id
            )
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
            raw_data_detail = sp_promotion.get_discount(discount_id=mp_promotion_id)
            item_list = []
            if 'item_list' in raw_data_detail:
                item_list = raw_data_detail['item_list']
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'discount',
                    'name': raw_data_detail['discount_name'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['start_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['discount_id']
                },
                # mapping spesific type promotion fields
                'discount': {
                    'item_list': item_list
                },
                'voucher': {},
                'bundle': {},
                'addon': {}
            })

            # cleaning key after mapping
            if 'item_list' in raw_data_detail:
                raw_data_detail.pop('item_list')
            raw_data_detail.pop('more')

            sp_discount_data_raw, sp_discount_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=raw_data_detail)
            sp_discount_raws.append(sp_discount_data_raw)
            sp_discount_sanitizeds.append(sp_discount_data_sanitized)

        if sp_discount_raws and sp_discount_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_promotion_id',
                'raw_data': sp_discount_raws,
                'mp_data': sp_discount_sanitizeds,
                'multi': isinstance(sp_discount_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_voucher(self, **kw):
        _logger = self.env['mp.base']._logger
        sp_promotion = kw.get('sp_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        sp_promotion_by_mpexid = kw.get('sp_promotion_by_mpexid')
        mp_promotion_obj = self.env['mp.promotion.program']

        def mapping_voucher_raw(raw_data_detail):
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'voucher',
                    'name': raw_data_detail['voucher_name'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['start_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['voucher_id'],
                    'is_uploaded': True
                },
                # mapping spesific type promotion fields
                'discount': {},
                'voucher': {
                    'voucher_code': raw_data_detail['voucher_code'],
                    'voucher_type': raw_data_detail['voucher_type'],
                    'reward_type': raw_data_detail['reward_type'],
                    'usage_quantity': raw_data_detail['usage_quantity'],
                    'current_usage': raw_data_detail['current_usage'],
                    'discount_amount': raw_data_detail.get('discount_amount', None),
                    'item_id_list': raw_data_detail.get('item_id_list', []),
                    'percentage': raw_data_detail.get('percentage', None),
                    'max_price': raw_data_detail.get('max_price', None),
                    'min_basket_price': raw_data_detail['min_basket_price'],
                    'display_channel_list': raw_data_detail.get('display_channel_list', []),
                },
                'bundle': {},
                'addon': {},
            })
            return raw_data_detail

        sp_voucher_raws, sp_voucher_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': ['upcoming', 'ongoing']  # Available value: upcoming/ongoing/expired/all.
            }
            sp_voucher_list = sp_promotion.get_voucher_list(**params)
            if 'message' in sp_voucher_list and sp_voucher_list.get('message') != '':
                raise UserError('Shopee API error with the code: %s caused by %s' % (sp_voucher_list.get('error'), sp_voucher_list.get('message')))
            if sp_voucher_list:
                for index, sp_data_voucher in enumerate(sp_voucher_list):
                    notif_msg = "(%s/%d) Getting voucher detail of %s... Please wait!" % (
                        str(index + 1), len(sp_voucher_list), sp_data_voucher.get('voucher_id')
                    )
                    # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    raw_data_detail = sp_promotion.get_voucher(voucher_id=sp_data_voucher.get(
                        'voucher_id'), status=sp_data_voucher.get('status'))
                    raw_data_detail = mapping_voucher_raw(raw_data_detail)

                    # cleaning key after mapping
                    new_raw_data_detail = raw_data_detail.copy()
                    for key in raw_data_detail:
                        if key in new_raw_data_detail['voucher']:
                            del new_raw_data_detail[key]

                    sp_voucher_data_raw, sp_voucher_data_sanitized = mp_promotion_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
                    sp_voucher_raws.append(sp_voucher_data_raw)
                    sp_voucher_sanitizeds.append(sp_voucher_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting voucher detail of %s... Please wait!" % (
                mp_promotion_id
            )
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
            raw_data_detail = sp_promotion.get_voucher(voucher_id=mp_promotion_id)
            raw_data_detail = mapping_voucher_raw(raw_data_detail)
            # cleaning key after mapping
            new_raw_data_detail = raw_data_detail.copy()
            for key in raw_data_detail:
                if key in new_raw_data_detail['voucher']:
                    del new_raw_data_detail[key]

            sp_voucher_data_raw, sp_voucher_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
            sp_voucher_raws.append(sp_voucher_data_raw)
            sp_voucher_sanitizeds.append(sp_voucher_data_sanitized)

        if sp_voucher_raws and sp_voucher_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_promotion_id',
                'raw_data': sp_voucher_raws,
                'mp_data': sp_voucher_sanitizeds,
                'multi': isinstance(sp_voucher_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_bundle_deal(self, **kw):
        _logger = self.env['mp.base']._logger
        sp_promotion = kw.get('sp_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        sp_promotion_by_mpexid = kw.get('sp_promotion_by_mpexid')
        mp_promotion_obj = self.env['mp.promotion.program']

        def mapping_bundle_raw(raw_data_detail):
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'bundle',
                    'name': raw_data_detail['name'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['start_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['bundle_deal_id'],
                    'is_uploaded': True
                },
                # mapping spesific type promotion fields
                'discount': {},
                'voucher': {},
                'bundle': {
                    'rule_type': raw_data_detail['bundle_deal_rule']['rule_type'],
                    'discount_value': raw_data_detail['bundle_deal_rule'].get('discount_value', None),
                    'fix_price': raw_data_detail['bundle_deal_rule'].get('fix_price', None),
                    'discount_percentage': raw_data_detail['bundle_deal_rule'].get('discount_percentage', None),
                    'min_amount': raw_data_detail['bundle_deal_rule'].get('min_amount', None),
                    'purchase_limit': raw_data_detail.get('purchase_limit', None),
                    'item_list': []
                },
                'addon': {},
            })
            return raw_data_detail

        sp_bundle_raws, sp_bundle_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': [2, 3, 4]  # Available value: upcoming:2/ongoing:3/expired:4/all:1.
            }
            sp_bundle_list = sp_promotion.get_bundle_list(**params)
            if 'message' in sp_bundle_list and sp_bundle_list.get('message') != '':
                raise UserError('Shopee API error with the code: %s caused by %s' % (sp_bundle_list.get('error'), sp_bundle_list.get('message')))
            if sp_bundle_list:
                for index, sp_data_bundle in enumerate(sp_bundle_list):
                    notif_msg = "(%s/%d) Getting bundle deal detail of %s... Please wait!" % (
                        str(index + 1), len(sp_bundle_list), sp_data_bundle.get('bundle_deal_id')
                    )
                    # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    raw_data_detail = sp_promotion.get_bundle(bundle_deal_id=sp_data_bundle.get(
                        'bundle_deal_id'), status=sp_data_bundle.get('status'))
                    raw_data_detail = mapping_bundle_raw(raw_data_detail)
                    bundle_item_raw = sp_promotion.get_bundle_item(bundle_deal_id=sp_data_bundle.get(
                        'bundle_deal_id'))
                    raw_data_detail['bundle']['item_list'].extend(bundle_item_raw)

                    # cleaning key after mapping
                    new_raw_data_detail = raw_data_detail.copy()
                    for key in raw_data_detail:
                        if key in new_raw_data_detail['bundle']:
                            del new_raw_data_detail[key]

                    sp_bundle_data_raw, sp_bundle_data_sanitized = mp_promotion_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
                    sp_bundle_raws.append(sp_bundle_data_raw)
                    sp_bundle_sanitizeds.append(sp_bundle_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting bundle deal detail of %s... Please wait!" % (
                mp_promotion_id
            )
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
            raw_data_detail = sp_promotion.get_bundle(bundle_deal_id=mp_promotion_id)
            raw_data_detail = mapping_bundle_raw(raw_data_detail)
            bundle_item_raw = sp_promotion.get_bundle_item(bundle_deal_id=mp_promotion_id)
            raw_data_detail['bundle']['item_list'].extend(bundle_item_raw)

            # cleaning key after mapping
            new_raw_data_detail = raw_data_detail.copy()
            for key in raw_data_detail:
                if key in new_raw_data_detail['bundle']:
                    del new_raw_data_detail[key]

            sp_bundle_data_raw, sp_bundle_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
            sp_bundle_raws.append(sp_bundle_data_raw)
            sp_bundle_sanitizeds.append(sp_bundle_data_sanitized)

        if sp_bundle_raws and sp_bundle_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_promotion_id',
                'raw_data': sp_bundle_raws,
                'mp_data': sp_bundle_sanitizeds,
                'multi': isinstance(sp_bundle_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_add_on_deal(self, **kw):
        _logger = self.env['mp.base']._logger
        sp_promotion = kw.get('sp_promotion')
        mp_account_ctx = kw.get('mp_account_ctx')
        sp_promotion_by_mpexid = kw.get('sp_promotion_by_mpexid')
        mp_promotion_obj = self.env['mp.promotion.program']

        def mapping_addon_raw(raw_data_detail):
            raw_data_detail.update({
                # mapping base info promotion
                'base_info': {
                    'type': 'addon',
                    'name': raw_data_detail['add_on_deal_name'],
                    'status': raw_data_detail['status'],
                    'start_time': raw_data_detail['start_time'],
                    'end_time': raw_data_detail['end_time'],
                    'promotion_id': raw_data_detail['add_on_deal_id'],
                    'is_uploaded': True
                },
                # mapping spesific type promotion fields
                'discount': {},
                'voucher': {},
                'bundle': {},
                'addon': {
                    'promotion_type': raw_data_detail.get('promotion_type', None),
                    'purchase_min_spend': raw_data_detail.get('purchase_min_spend', None),
                    'promotion_purchase_limit': raw_data_detail.get('promotion_purchase_limit', None),
                    'per_gift_num': raw_data_detail.get('per_gift_num', None),
                    'main_item': [],
                    'sub_item': [],
                },
            })
            return raw_data_detail

        sp_addon_raws, sp_addon_sanitizeds = [], []
        if kw.get('params') == 'by_default':
            params = {
                'status': ['upcoming', 'ongoing']  # Available value: upcoming/ongoing/expired/all.
            }
            sp_addon_list = sp_promotion.get_addon_deal_list(**params)
            if 'message' in sp_addon_list and sp_addon_list.get('message') != '':
                raise UserError('Shopee API error with the code: %s caused by %s' % (sp_addon_list.get('error'), sp_addon_list.get('message')))
            if sp_addon_list:
                for index, sp_data_addon in enumerate(sp_addon_list):
                    notif_msg = "(%s/%d) Getting addon deal detail of %s... Please wait!" % (
                        str(index + 1), len(sp_addon_list), sp_data_addon.get('add_on_deal_id')
                    )
                    # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                    raw_data_detail = sp_promotion.get_addon_deal(addon_deal_id=sp_data_addon.get(
                        'add_on_deal_id'), status=sp_data_addon.get('status'))
                    raw_data_detail = mapping_addon_raw(raw_data_detail)

                    # Getting main item addon
                    addon_main_item_raw = sp_promotion.get_addon_main_item(addon_deal_id=sp_data_addon.get(
                        'add_on_deal_id'))
                    raw_data_detail['addon']['main_item'].extend(addon_main_item_raw)

                    # Getting sub item addon
                    addon_sub_item_raw = sp_promotion.get_addon_sub_item(addon_deal_id=sp_data_addon.get(
                        'add_on_deal_id'))
                    raw_data_detail['addon']['sub_item'].extend(addon_sub_item_raw)

                    # cleaning key after mapping
                    new_raw_data_detail = raw_data_detail.copy()
                    for key in raw_data_detail:
                        if key in new_raw_data_detail['addon']:
                            del new_raw_data_detail[key]

                    sp_addon_data_raw, sp_addon_data_sanitized = mp_promotion_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
                    sp_addon_raws.append(sp_addon_data_raw)
                    sp_addon_sanitizeds.append(sp_addon_data_sanitized)

        elif kw.get('params') == 'by_mp_promotion_id':
            mp_promotion_id = int(kw.get('mp_promotion_id'))
            notif_msg = "Getting add on deal detail of %s... Please wait!" % (
                mp_promotion_id
            )
            raw_data_detail = sp_promotion.get_addon_deal(addon_deal_id=mp_promotion_id)
            raw_data_detail = mapping_addon_raw(raw_data_detail)

            # Getting main item addon
            addon_main_item_raw = sp_promotion.get_addon_main_item(addon_deal_id=mp_promotion_id)
            raw_data_detail['addon']['main_item'].extend(addon_main_item_raw)

            # Getting sub item addon
            addon_sub_item_raw = sp_promotion.get_addon_sub_item(addon_deal_id=mp_promotion_id)
            raw_data_detail['addon']['sub_item'].extend(addon_sub_item_raw)

            # cleaning key after mapping
            new_raw_data_detail = raw_data_detail.copy()
            for key in raw_data_detail:
                if key in new_raw_data_detail['addon']:
                    del new_raw_data_detail[key]

            sp_addon_data_raw, sp_addon_data_sanitized = mp_promotion_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=new_raw_data_detail)
            sp_addon_raws.append(sp_addon_data_raw)
            sp_addon_sanitizeds.append(sp_addon_data_sanitized)

        if sp_addon_raws and sp_addon_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'sp_promotion_id',
                'raw_data': sp_addon_raws,
                'mp_data': sp_addon_sanitizeds,
                'multi': isinstance(sp_addon_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_get_promotion(self, **kw):
        self.ensure_one()
        params = {}
        mp_account_ctx = self.generate_context()
        mp_promotion_obj = self.env['mp.promotion.program']
        _notify = self.env['mp.base']._notify

        # fetch all exist sp promotion data
        sp_promotion_by_mpexid = {}
        sp_promotion_recs = mp_promotion_obj.search(
            [('mp_account_id', '=', self.id), ('company_id', '=', self.company_id.id)])
        for sp_promotion_rec in sp_promotion_recs:
            sp_promotion_by_mpexid[sp_promotion_rec.sp_promotion_id] = sp_promotion_rec

        if self.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_token_id.name}
            sp_account = self.shopee_get_account(**params)
            sp_promotion = ShopeePromotion(sp_account)
            kw.update({
                'sp_promotion': sp_promotion,
                'mp_account_ctx': mp_account_ctx,
                'sp_promotion_by_mpexid': sp_promotion_by_mpexid
            })
            # _notify('info', 'Importing promotion from {} is started... Please wait!'.format(self.marketplace.upper()),
            #         notif_sticky=False)

            if kw.get('promotion_type') == 'discount':
                self.shopee_get_discount(**kw)
            elif kw.get('promotion_type') == 'voucher':
                self.shopee_get_voucher(**kw)
            elif kw.get('promotion_type') == 'bundle':
                self.shopee_get_bundle_deal(**kw)
            elif kw.get('promotion_type') == 'addon':
                self.shopee_get_add_on_deal(**kw)
            else:
                self.shopee_get_discount(**kw)
                self.shopee_get_voucher(**kw)
                self.shopee_get_bundle_deal(**kw)
                self.shopee_get_add_on_deal(**kw)

        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
