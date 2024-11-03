# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from datetime import datetime, timedelta
import io
import time
import logging
_logger = logging.getLogger(__name__)
from Cryptodome.PublicKey import RSA
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import mp, json_digger, generate_id

from odoo.addons.izi_tokopedia.objects.utils.tokopedia.account import TokopediaAccount
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.encryption import TokopediaEncryption
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.logistic import TokopediaLogistic
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order import TokopediaOrder
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.category import TokopediaCategory
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.product import TokopediaProduct
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.shop import TokopediaShop
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.webhook import TokopediaWebhook
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.campaign import TokopediaCampaign
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.api import TokopediaAPI


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'
    _sql_constraints = [
        ('unique_tp_shop_url', 'UNIQUE(tp_shop_url)', 'This URL is already registered, please try another shop URL!')
    ]

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    # marketplace = fields.Selection(selection_add=[('tokopedia', 'Tokopedia')], ondelete={'tokopedia': 'cascade'})
    tp_client_id = fields.Char(string="Tokopedia Client ID",
                               required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_client_secret = fields.Char(string="Tokopedia Client Secret",
                                   required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_fs_id = fields.Char(string="Fulfillment Service ID", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_url = fields.Char(string="Shop URL", required_if_marketplace="tokopedia", states=READONLY_STATES)
    tp_shop_id = fields.Many2one(comodel_name="mp.tokopedia.shop", string="Tokopedia Current Shop",
                                 readonly=True, ondelete='set null')
    tp_private_key_file = fields.Text(string="Secret Key File")
    # tp_private_key_file_name = fields.Char(string="Secret Key File Name")
    tp_private_key = fields.Char(string="Secret Key", compute="_compute_tp_private_key")
    tp_public_key_file = fields.Text(string="Public Key File")
    # tp_public_key_file_name = fields.Char(string="Public Key File Name")
    tp_public_key = fields.Char(string="Public Key", compute="_compute_tp_public_key")

    tp_webhook_secret = fields.Char(string='Tokopedia Webhook Secret')
    tp_is_webhook_order = fields.Boolean(string='Tokopedia Order Webhook', default=True)

    ### MULTI ###
    def _compute_tp_private_key(self):
        self.tp_private_key = None
        for rec in self.filtered(lambda r: (r.marketplace == 'tokopedia') and r.tp_private_key_file):
            rec.tp_private_key = rec.with_context({'bin_size': False}).tp_private_key_file

    ### MULTI ###
    def _compute_tp_public_key(self):
        self.tp_public_key = None
        for rec in self.filtered(lambda r: (r.marketplace == 'tokopedia') and r.tp_public_key_file):
            rec.tp_public_key = rec.with_context({'bin_size': False}).tp_public_key_file

    ### MULTI ###
    def generate_rsa_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()
        key = RSA.generate(2048)
        private_key, public_key = key.export_key().decode('utf-8'), key.publickey().export_key().decode('utf-8')
        self.write({
            'tp_private_key_file': private_key,
            'tp_public_key_file': public_key
        })
        # _notify('info', "New RSA key generated successfully!")
        if self._context.get('get_private_key'):
            return private_key
        if self._context.get('get_public_key'):
            return public_key
        if self._context.get('get_pair_key'):
            return private_key, public_key

    @api.model
    def tokopedia_get_account(self, **kwargs):
        credentials = dict({
            'client_id': self.tp_client_id,
            'client_secret': self.tp_client_secret,
            # 'fs_id': int(self.tp_fs_id),
            'fs_id': self.tp_fs_id,
            'access_token': self.access_token,
            'expired_date': fields.Datetime.from_string(self.access_token_expired_date),
            'token_type': self.mp_token_id.tp_token_type,
            'shop_id': kwargs.get('shop_id', int(self.tp_shop_id.shop_id))
        }, **kwargs)
        tp_account = TokopediaAccount(**credentials)
        return tp_account

    # @api.multi
    def tokopedia_authenticate(self):
        _notify = self.env['mp.base']._notify
        mp_token_obj = self.env['mp.token']

        self.ensure_one()
        tp_account = self.tokopedia_get_account()
        raw_token = tp_account.tp_authenticate()
        if 'error' in raw_token:
            # _notify('danger', 'Error: %s. \n %s' % (raw_token.get('error'), raw_token.get('error_description')))
            _logger.info('Error: %s. \n %s' % (raw_token.get('error'), raw_token.get('error_description')))
        mp_token_obj.create_token(self, raw_token)
        res = self.write({
                    'state': 'authenticated',
                    'auth_message': 'Congratulations, you have been successfully authenticated!'
                })
        return res

    # @api.multi
    def tokopedia_upload_public_key(self):
        return {
            'name': 'Upload Key Pair',
            'view_mode': 'form',
            'res_model': 'wiz.upload_public_key',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_mp_account_id': self.id,
            },
        }

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_register_public_key(self):
        _notify = self.env['mp.base']._notify

        self.ensure_one()

        if self.with_context({'bin_size': False}).tp_public_key_file:
            public_key = io.StringIO(self.with_context({'bin_size': False}).tp_public_key_file)
        else:
            public_key = io.StringIO(self.with_context({'get_public_key': True}).generate_rsa_key())

        tp_account = self.tokopedia_get_account()
        tp_encryption = TokopediaEncryption(tp_account)
        response = tp_encryption.register_public_key(public_key)
        # if response.status_code == 200:
        #     _notify('info', 'Public key registered successfully!')

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_register_webhooks(self):
        _logger = self.env['mp.base']._logger
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.ensure_one()

        if not self.tp_webhook_secret:
            raise UserError('Webhook secret must be filled')

        webhook_args = {
            'webhook_secret': self.tp_webhook_secret
        }

        if self.fields_get().get('tp_is_webhook_order', False):
            if self.tp_is_webhook_order:
                webhook_args.update({
                    'order_notification_url': base_url + '/api/izi/webhook/tp/order/notification',
                    'order_request_cancellation_url': base_url + '/api/izi/webhook/tp/order/request/cancel',
                    'order_status_url': base_url + '/api/izi/webhook/tp/order/status'
                })
        if len(webhook_args) > 1:
            tp_account = self.tokopedia_get_account()
            tp_webhook = TokopediaWebhook(tp_account)
            response = tp_webhook.register_webhook(**webhook_args)
            if response.status_code == 200:
                notif_msg = "Register webhook is successfully.."
                self.write({
                    'mp_webhook_state': 'registered'
                })
            else:
                notif_msg = "Register webhook is failure.."
                self.write({
                    'mp_webhook_state': 'no_register'
                })
            # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
        else:
            raise UserError('Select at least 1 feature for register webhook')

    @mp.tokopedia.capture_error
    def tokopedia_unregister_webhooks(self):
        _logger = self.env['mp.base']._logger
        notif_msg = "Unregister webhook is Success.."
        self.write({
            'mp_webhook_state': 'no_register'
        })
        # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_shop(self):
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tokopedia_shop_obj = self.env['mp.tokopedia.shop'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_shop = TokopediaShop(tp_account, sanitizers=mp_tokopedia_shop_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        tp_data_raw, tp_data_sanitized = tp_shop.get_shop_info()
        check_existing_records_params = {
            'identifier_field': 'shop_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_raw,
            'multi': isinstance(tp_data_raw, list)
        }
        check_existing_records = mp_tokopedia_shop_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_shop_obj.handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_logistics(self):
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_tokopedia_logistic_obj = self.env['mp.tokopedia.logistic'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_logistic = TokopediaLogistic(tp_account, api_version="v2",
                                        sanitizers=mp_tokopedia_logistic_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing logistic from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        tp_data_raw, tp_data_sanitized = tp_logistic.get_logistic_info(shop_id=self.tp_shop_id.shop_id)
        check_existing_records_params = {
            'identifier_field': 'shipper_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_tokopedia_logistic_obj.check_existing_records(**check_existing_records_params)
        mp_tokopedia_logistic_obj.handle_result_check_existing_records(check_existing_records)

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.tp_shop_id.with_context(mp_account_ctx).get_active_logistics()

    @mp.tokopedia.capture_error
    def tokopedia_get_category(self):
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        mp_category_obj = self.env['mp.tokopedia.category'].with_context(mp_account_ctx)

        self.ensure_one()

        tp_account = self.tokopedia_get_account()
        tp_category = TokopediaCategory(tp_account, api_version="v1",
                                        sanitizers=mp_category_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing category from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)
        tp_raw, tp_data = tp_category.get_category_info(shop_id=self.tp_shop_id.shop_id)
        mp_data_raw = mp_category_obj.tp_generate_category_data(tp_raw, mp_account_id)
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

    def tokopedia_get_attribute(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        rec.tokopedia_get_attribute_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @mp.tokopedia.capture_error
    def tokopedia_get_attribute_data(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        _notify = self.env['mp.base']._notify
        self.env.cr.execute(
            'UPDATE mp_tokopedia_category SET attribute_mapped=true, variant_mapped=true WHERE parent_category_id=0 AND (attribute_mapped is null or attribute_mapped=false)'
        )

        mp_category_obj = self.env['mp.tokopedia.category'].search([('has_children', '=', False), ('parent_category_id', '!=', 0), ('attribute_mapped', '=', False)], order="category_id asc", limit=20)
        mp_attribute_obj = self.env['mp.tokopedia.attribute'].with_context(mp_account_ctx)

        tp_account = self.tokopedia_get_account()
        tp_category = TokopediaCategory(tp_account, api_version="v1",
                                        sanitizers=mp_attribute_obj.get_sanitizers(self.marketplace))
        tp_categ_variant = TokopediaCategory(tp_account, api_version="v2")
        # _notify('info', 'Importing attribute & Variant from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

        cron_name = 'IZI Tokopedia Attribute Scheduler %s' % (str(mp_account_id))
        cron_order = self.env['ir.cron'].sudo().search([('name', '=', cron_name), ('active', '=', True)])
        delta_var = 'seconds'
        interval = 30
        next_call = datetime.now() - eval(f'timedelta({delta_var}={interval})')

        if mp_category_obj:
            for data in mp_category_obj:
                tp_attrib_raw = False
                response = tp_category.get_attributes_info(shop_id=self.tp_shop_id.shop_id, category_id=data.category_id)
                if response.status_code == 200:
                    tp_attrib_raw = json.loads(response.text, strict=False)['data']
                    if tp_attrib_raw:
                        for index, dattrib in enumerate(tp_attrib_raw):
                            tp_attrib_raw[index].update({'category_id': data.category_id})
                        mp_data_raw = mp_attribute_obj.tp_generate_attribute_data(tp_attrib_raw, mp_account_id)
                        tp_data_raws, tp_data_sanitizeds = mp_attribute_obj.with_context(
                            mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_data_raw)
                        check_existing_records_params = {
                            'identifier_field': 'tp_category_id',
                            'raw_data': tp_data_raws,
                            'mp_data': tp_data_sanitizeds,
                            'multi': isinstance(tp_data_sanitizeds, list)
                        }
                        check_existing_records = mp_attribute_obj.with_context(
                            mp_account_ctx).check_existing_records(**check_existing_records_params)
                        mp_attribute_obj.with_context(
                            mp_account_ctx).handle_result_check_existing_records(check_existing_records)
                    self.env.cr.execute(
                        'UPDATE mp_tokopedia_category SET attribute_mapped=true, variant_mapped=true WHERE category_id=%s',
                        (data.category_id,)
                    )
                ### for mp.tokopedia.variant
                # mp_variant_obj = self.env['mp.tokopedia.variant'].with_context(mp_account_ctx)
                mp_variant_obj = self.env['mp.product.variant'].with_context(mp_account_ctx)
                var_response = tp_categ_variant.get_variants_info(shop_id=self.tp_shop_id.shop_id,
                                                           category_id=data.category_id)
                if var_response.status_code == 200:
                    tp_variant_raw = json.loads(var_response.text, strict=False)['data']
                    if tp_variant_raw:
                        mp_data_raw = mp_variant_obj.tp_generate_variant_data(tp_variant_raw)
        # else:
            # time.sleep(45)
            # if cron_order:
                # cron_order.sudo().write({
                #     'nextcall': next_call,
                #     'active': False
                # })

    # @api.multi
    def tokopedia_get_dependencies(self):
        self.ensure_one()
        self.tokopedia_get_shop()
        self.tokopedia_get_logistics()
        self.tokopedia_get_active_logistics()
        tp_data_raw, tp_data_sanitized = self.tokopedia_get_category()
        mp_account_ctx = self.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        cron_name = 'IZI Tokopedia Attribute Scheduler %s' % (str(mp_account_id))
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
        }

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_mp_product(self, **kwargs):
        _notify = self.env['mp.base']._notify
        mp_product_obj = self.env['mp.product']

        self.ensure_one()

        mp_account_ctx = self.generate_context()
        tp_account = self.tokopedia_get_account()
        tp_product = TokopediaProduct(tp_account, sanitizers=mp_product_obj.get_sanitizers(self.marketplace))
        # _notify('info', 'Importing product from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

        if kwargs.get('product_ids'):
            # get single product
            # product_ids = list(map(str, kwargs.get('product_ids')))
            tp_data_raw, tp_data_sanitized = tp_product.get_product_info(product_id=kwargs.get('product_ids'))
            # existing_mp_products = mp_product_obj.search(
            #     [('mp_account_id', '=', self.id), ('mp_external_id', 'in', product_ids)])
        else:
            # get batch product
            tp_data_raw, tp_data_sanitized = tp_product.get_product_info(shop_id=self.tp_shop_id.shop_id,
                                                                         limit=mp_account_ctx.get('product_limit'))

            # existing_mp_products = mp_product_obj.search([('mp_account_id', '=', self.id)])
        # tp_product_exid = list(map(lambda x: str(x['basic']['productID']), tp_data_raw))
        # mp_product_need_to_archive = []
        # for mp_product in existing_mp_products:
        #     if mp_product.mp_external_id not in tp_product_exid:
        #         mp_product_need_to_archive.append(mp_product.mp_external_id)

        check_existing_records_params = {
            'identifier_field': 'tp_product_id',
            'raw_data': tp_data_raw,
            'mp_data': tp_data_sanitized,
            'multi': isinstance(tp_data_sanitized, list)
        }
        check_existing_records = mp_product_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        mp_product_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

        ### create or update mp_stock for product
        if tp_data_raw:
            mp_stock_obj = self.env['mp.stock']
            mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=tp_data_raw)

        # archive mp_product if doesnt exists in marketplace
        # mp_products_archive = existing_mp_products.filtered(lambda r: r.mp_external_id in mp_product_need_to_archive)
        # for product in mp_products_archive:
        #     for variant in product.mp_product_variant_ids:
        #         variant.active = False
        #     product.active = False

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_mp_product_variant(self, **kwargs):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        tp_account = self.tokopedia_get_account()
        tp_product_variant = TokopediaProduct(tp_account,
                                              sanitizers=mp_product_variant_obj.get_sanitizers(self.marketplace))

        if kwargs.get('product_ids'):
            if type(kwargs.get('product_ids')) == int:
                product_ids = [kwargs.get('product_ids')]
            else:
                product_ids = list(map(str, kwargs.get('product_ids')))
            mp_products = mp_product_obj.search(
                [('mp_external_id', 'in', product_ids),
                 ('mp_account_id', '=', self.id),
                 ('tp_has_variant', '=', True)])
        else:
            mp_products = mp_product_obj.search([('tp_has_variant', '=', True), ('mp_account_id', '=', self.id)])

        tp_data_raws, tp_data_sanitizeds = [], []
        tp_variant_ids = []
        for mp_product in mp_products:
            variant_need_to_remove = []
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            tp_variant_ids.extend(json_digger(mp_product_raw, 'variant/childrenID'))
            # mp_variant_exid_list = json_digger(mp_product_raw, 'variant/childrenID')

            # for variant_obj in mp_product.mp_product_variant_ids:
            #     if int(variant_obj.tp_variant_id) not in mp_variant_exid_list:
            #         variant_need_to_remove.append(variant_obj.tp_variant_id)

            # archive variant
            # mp_product.mp_product_variant_ids.filtered(lambda r: r.tp_variant_id in variant_need_to_remove).write({
            #     'active': False
            # })

        tp_variant_ids_splited = mp_product_variant_obj.create_chunks(tp_variant_ids, 500)
        for tp_variant_ids in tp_variant_ids_splited:
            tp_data_raw, tp_data_sanitized = tp_product_variant.get_product_info(product_id=tp_variant_ids)
            tp_data_raws.extend(tp_data_raw)
            tp_data_sanitizeds.extend(tp_data_sanitized)

        check_existing_records_params = {
            'identifier_field': 'tp_variant_id',
            'raw_data': tp_data_raws,
            'mp_data': tp_data_sanitizeds,
            'multi': isinstance(tp_data_sanitizeds, list)
        }
        check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
            **check_existing_records_params)
        mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
            check_existing_records)

        ### create or update mp_stock for product variant
        if tp_data_raws:
            mp_stock_obj = self.env['mp.stock']
            mp_stock_obj.mp_create_update_stock(mp_account_id=mp_account_ctx.get('mp_account_id'), raw_product=tp_data_raws, map_type='variant')
        # # archive variant
        # mp_products = mp_product_obj.search([('mp_product_variant_ids', '!=', False),
        #                                     ('tp_has_variant', '=', False),
        #                                     ('mp_account_id', '=', self.id)])
        # for product in mp_products:
        #     for variant in product.mp_product_variant_ids:
        #         variant.active = False

    # @api.multi
    def tokopedia_get_products(self, **kwargs):
        self.ensure_one()
        self.tokopedia_get_mp_product(**kwargs)
        self.tokopedia_get_mp_product_variant(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def tokopedia_get_orders_detail_test(self, **params):
        tp_data_raw = [] 
        tp_data_sanitized = []
        if params.get('order_ids'):
            for order_id in params.get('order_ids'):
                order_raw = self.env['ir.config_parameter'].sudo().get_param('mp.test.tp.order.raw')
                order_sanitized = self.env['ir.config_parameter'].sudo().get_param('mp.test.tp.order.sanitized')
                if not order_raw or not order_sanitized:
                    raise UserError('Set order template in mp.test.tp.order.raw in system parameter!')
                order_raw_vals = eval(order_raw)
                order_sanitized_vals = eval(order_sanitized)
                order_raw_vals.update({
                    'order_id': order_id,
                    'invoice_number': order_id,
                })
                for index, order_detail in enumerate(order_raw_vals['order_info']['order_detail']):
                    order_detail.update({
                        'order_detail_id': '%s-%s' % (str(order_id), str(index))
                    })
                order_sanitized_vals.update({
                    'mp_external_id': order_id,
                    'tp_order_id': order_id,
                    'mp_invoice_number': order_id,
                })
                tp_data_raw.append(order_raw_vals)
                tp_data_sanitized.append(order_sanitized_vals)
        return tp_data_raw, tp_data_sanitized

    # @api.multi
    @mp.tokopedia.capture_error
    def tokopedia_get_sale_order(self, **kwargs):
        mp_account_ctx = self.generate_context()
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        datetime_convert_tz = self.env['mp.base'].datetime_convert_tz

        self.ensure_one()

        self.tokopedia_register_public_key()

        tp_account = self.tokopedia_get_account()
        tp_order = TokopediaOrder(tp_account, api_version="v2")
        # _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

        skipped = 0
        force_update_ids = []
        params, tp_data_detail_orders = {}, []
        tp_data_raws, tp_data_sanitizeds = [], []
        if kwargs.get('params') == 'by_date_range':
            tp_orders_by_mpexid = {}
            tp_orders = order_obj.search([('mp_account_id', '=', self.id),
                                         ('tp_order_status', 'not in', ['700', '701'])])
            for rec_tp_order in tp_orders:
                tp_orders_by_mpexid[rec_tp_order.tp_order_id] = rec_tp_order
            params.update({
                'from_date': kwargs.get('from_date'),
                'to_date': kwargs.get('to_date'),
                'shop_id': self.tp_shop_id.shop_id,
                'limit': mp_account_ctx.get('order_limit')
            })
            tp_data_orders = tp_order.get_order_list(**params)
            if tp_data_orders:
                for index, tp_data_order in enumerate(tp_data_orders):
                    tp_invoice_number = tp_data_order.get('invoice_ref_num')
                    tp_order_id = tp_data_order.get('order_id')
                    # print('tp_order_id: %s' % tp_order_id)
                    if tp_order_id and tp_order_id in tp_orders_by_mpexid:
                        existing_order = tp_orders_by_mpexid[tp_order_id]
                        mp_status_changed = existing_order.tp_order_status != str(tp_data_order['order_status'])
                    else:
                        existing_order = False
                        mp_status_changed = False
                    # If no existing order OR mp status changed on existing order, then fetch new detail order
                    no_existing_order = not existing_order
                    if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                        tp_status_cancel = ['0', '2', '3', '4', '5', '10', '15', '690', '691', '695', '698', '699']
                        if str(tp_data_order['order_status']) in tp_status_cancel and no_existing_order:
                            if not self.get_cancelled_orders:
                                skipped += 1
                                continue
                        if existing_order:
                            force_update_ids.append(existing_order.id)
                        notif_msg = "(%s/%d) Getting order detail of %s... Please wait!" % (
                            str(index + 1), len(tp_data_orders), tp_invoice_number
                        )
                        # _logger(self.marketplace, notif_msg, notify=True, notif_sticky=False)
                        time.sleep(0.02)
                        if tp_order_id:
                            tp_data_detail_order = tp_order.get_order_detail(order_ids=[tp_order_id])[0]
                            tp_data_detail_order.update({'order_summary': tp_data_order, 'branch_id': self.branch_id.id})
                            tp_data_detail_orders.append(tp_data_detail_order)
                            tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                                raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
                            tp_data_raws.extend(tp_data_raw)
                            tp_data_sanitizeds.extend(tp_data_sanitized)
                    else:
                        skipped += 1

            # _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
            #     len(tp_data_detail_orders), len(tp_data_orders)
            # ), notify=True, notif_sticky=False)
        elif kwargs.get('params') == 'by_mp_invoice_number':
            tokopedia_invoice_number, tokopedia_order_id = [], []
            mp_invoice_number = kwargs.get('mp_invoice_number', False)
            if type(mp_invoice_number) == str:
                tokopedia_invoice_number = [inv for inv in mp_invoice_number.split(',')]
            else:
                tokopedia_invoice_number = mp_invoice_number

            mp_order_id = kwargs.get('mp_order_id', False)
            if type(mp_order_id) == str:
                tokopedia_order_id = [order_id for order_id in mp_order_id.split(',')]
            else:
                tokopedia_order_id = mp_order_id
            if tokopedia_order_id or tokopedia_invoice_number:
                params.update({'invoice_num_ids': tokopedia_invoice_number,
                               'order_ids': tokopedia_order_id,
                               'show_log': True,
                               'get_order_summary': True,
                               'shop_id': self.tp_shop_id.shop_id})
                # Check If Marketplace Test (mp.test)
                mp_test = self.env['ir.config_parameter'].sudo().get_param('mp.test')
                if mp_test:
                    tp_data_raw, tp_data_sanitized = self.tokopedia_get_orders_detail_test(**params)
                else:
                    tp_data_detail_order = tp_order.get_order_detail(**params)
                    tp_data_raw, tp_data_sanitized = order_obj._prepare_mapping_raw_data(
                        raw_data=tp_data_detail_order, endpoint_key='sanitize_decrypt')
                # _logger(self.marketplace, 'TOKOPEDIA_ORDER > Raw %s' % (str(tp_data_raw)), notify=True, notif_sticky=False)
                # _logger(self.marketplace, 'TOKOPEDIA_ORDER > Sanitized %s' % (str(tp_data_sanitized)), notify=True, notif_sticky=False)
                tp_data_raws.extend(tp_data_raw)
                tp_data_sanitizeds.extend(tp_data_sanitized)

        if force_update_ids:
            order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                'force_update_ids': force_update_ids
            }))

        if tp_data_raws:
            check_existing_records_params = {
                'identifier_field': 'tp_order_id',
                'raw_data': tp_data_raws,
                'mp_data': tp_data_sanitizeds,
                'multi': isinstance(tp_data_sanitizeds, list)
            }
            check_existing_records = order_obj.check_existing_records(**check_existing_records_params)
            if kwargs.get('skip_create', False):
                check_existing_records.pop('need_create_records')
            order_obj.handle_result_check_existing_records(check_existing_records)
        # else:
        #     _logger(self.marketplace, 'There is no update, skipped %s order(s)!' % skipped, notify=True,
        #             notif_sticky=False)

    # @api.multi
    def tokopedia_get_orders(self, **kwargs):
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
        rec.tokopedia_get_sale_order(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    @mp.tokopedia.capture_error
    def tokopedia_get_saldo_history(self, **kwargs):
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
            from_date_str = (kwargs.get('from_date') + relativedelta(hours=7)).strftime("%Y/%m/%d")
            to_date_str = (kwargs.get('to_date')+relativedelta(hours=7)).strftime("%Y/%m/%d")
            bank_statement_raw.append({
                'name': 'Tokopedia Saldo: %s' % ((from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                'date': (from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                'journal_id': self.wallet_journal_id.id,
                'mp_start_date': from_date_str,
                'mp_end_date': to_date_str
            })
        else:
            if total_days >= 6:
                raise ValidationError('Date Range must be less than 6 days')
            for index in range(0, total_days):
                new_from_date = from_date + relativedelta(days=index)
                new_to_date = from_date + relativedelta(days=index)
                bank_statement_raw.append({
                    'name': 'Tokopedia Saldo: %s' % ((new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                    'date': (new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                    'journal_id': self.wallet_journal_id.id,
                    'mp_start_date': (new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                    'mp_end_date': (new_to_date + relativedelta(hours=7)).strftime("%Y/%m/%d")
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

    def tokopedia_auto_reconcile(self, **kwargs):
        _logger = self.env['mp.base']._logger
        if kwargs.get('bank_statement_list', False):
            bank_statement_list = kwargs.get('bank_statement_list')
            bank_statements = self.env['account.bank.statement'].search(
                [('mp_account_id', '=', self.id),
                 ('name', 'in', bank_statement_list)])
            if not bank_statements:
                raise UserError('Bank Statements is not found.')

            # invoice_lines = self.env['account.move.line'].search([
            #     ('move_id.move_type', '=', 'out_invoice'),
            #     ('reconciled', '=', False),
            #     ('account_internal_type', '=', 'receivable'),
            #     ('mp_account_id', '=', self.id),
            #     ('parent_state', '!=', 'cancel')
            # ])
            # invoice_by_mpexid = {}
            # for inv in invoice_lines:
            #     invoice_by_mpexid[inv.mp_invoice_number] = inv
            # wallet_statement_config = self.env['mp.wallet.statement.label'].sudo().search(
            #     [('mp_account_ids', 'in', self.id)])
            # reconcile_by_label = {}
            # for rb in wallet_statement_config.line_ids:
            #     reconcile_by_label[rb['name'].lower()] = rb

            for bank_statement in bank_statements:
                if bank_statement.state == 'open':
                    bank_statement.button_post()

            for bank_statement in bank_statements:
                if bank_statement.state == 'posted':
                    # _logger(self.marketplace, 'RECONCILE PROCESS FOR BANK STATEMENTS %s' % (bank_statement.name),
                    #         notify=True,
                    #         notif_sticky=False)

                    # New Method For Reconcile Process
                    bank_statement.process_bank_statement_reconciliation()

                    # move_lines = self.env['account.move.line'].search([
                    #     ('statement_id', '=', bank_statement.id),
                    #     ('reconciled', '=', False),
                    #     ('account_internal_type', '=', 'liquidity')
                    # ])
                    # index = 0
                    # move_lines = move_lines.filtered(lambda l: not l.statement_line_id.is_reconciled)
                    # for line in move_lines:
                    #     index += 1
                    #     st_line = line.statement_line_id
                    #     _logger(self.marketplace, '(%s/%s) RECONCILE MOVE LINES : %s' % (str(index), len(move_lines), st_line.mp_invoice_number),
                    #             notify=True,
                    #             notif_sticky=False)
                    #     if st_line.mp_invoice_number in invoice_by_mpexid:
                    #         _logger(self.marketplace, 'FOUND INVOICE NUMBER : %s ' % (st_line.mp_invoice_number),
                    #                 notify=True,
                    #                 notif_sticky=False)
                    #         if st_line.move_id.state != 'posted':
                    #             st_line.move_id._post(soft=False)
                    #         mp_invoice_number = st_line.mp_invoice_number
                    #         invoice = invoice_by_mpexid[mp_invoice_number]
                    #         if invoice.amount_residual_currency == st_line.amount:
                    #             st_line.partner_id = invoice.partner_id.id
                    #             if st_line.payment_ref.lower() in reconcile_by_label:
                    #                 rec_label = reconcile_by_label[st_line.payment_ref.lower()]
                    #                 if rec_label.action_type == 'reconcile':
                    #                     vals = [{
                    #                         'id': invoice.id,
                    #                     }]
                    #                     st_line.reconcile(vals, to_check=False)
                    #     if st_line.payment_ref.lower() in reconcile_by_label:
                    #         rec_label = reconcile_by_label[st_line.payment_ref.lower()]
                    #         if rec_label.action_type == 'manual':
                    #             for aml in st_line.line_ids:
                    #                 if aml.account_id != aml.journal_id.default_account_id:
                    #                     aml.write({'account_id': rec_label.account_id.id})


    @mp.tokopedia.capture_error
    def tokopedia_get_orders_wallet(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_range = kwargs.get('time_range', False)

        if time_range:
            if time_range == 'last_30_minutes':
                new_datetime = datetime.now()
                from_time = new_datetime - timedelta(minutes=30)
                to_time = new_datetime
            elif time_range == 'last_hours':
                new_datetime = datetime.now() - timedelta(hours=1)
                from_time = new_datetime - timedelta(minutes=30)
                to_time = new_datetime
            elif time_range == 'now':
                new_datetime = datetime.now()
                from_time = new_datetime
                to_time = new_datetime
            kwargs.update({
                'from_date': from_time,
                'to_date': to_time
            })
        bank_statement = rec.tokopedia_get_saldo_history(**kwargs)
        if kwargs.get('mode') in ['reconcile_only', 'both']:
            bank_statement_list = [data['name'] for data in bank_statement]
            auto_rec_param = {'bank_statement_list': bank_statement_list}
            rec.tokopedia_auto_reconcile(**auto_rec_param)
        mp_account_ctx = rec.generate_context()
        mp_account_id = mp_account_ctx.get('mp_account_id')
        cron_name = 'IZI Tokopedia Wallet Scheduler %s' % (str(mp_account_id))
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

    def tokopedia_set_product(self, **kw):
        self.ensure_one()
        tp_account = self.tokopedia_get_account()
        tp_account.endpoints.tp_account.shop_id = self.tp_shop_id.mp_external_id
        api = TokopediaAPI(tp_account)
        mp_product_ids = []
        params = ({
            'shop_id': self.tp_shop_id.mp_external_id
        })
        if kw.get('mode') == 'price_only':
            try:
                prepared_request = api.build_request('set_product_price', **{
                    'params': params
                })
                json_body = []
                for data in kw.get('data', []):
                    json_body.append({
                        'product_id': int(data['product_obj'].mp_external_id),
                        'new_price': int(data['price'])
                    })
                    if data['product_obj']._name == 'mp.product':
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                prepared_request = {**prepared_request, **{'json': json_body}}
                process_response = api.process_response('set_product_price', api.request(**prepared_request))
                # self.env['mp.base']._logger(self.marketplace, 'Product(s) updated', notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'stock_only':
            self.tokopedia_set_product(data=[{
                'product_obj': data['product_obj'],
                'activate': True,
            } for data in kw.get('data', [])], mode='activation')
            try:
                prepared_request = api.build_request('set_product_stock', **{
                    'params': params
                })
                json_body = []
                for data in kw.get('data', []):
                    json_body.append({
                        'product_id': int(data['product_obj'].mp_external_id),
                        'new_stock': int(data['stock'])
                    })
                    if data['product_obj']._name == 'mp.product':
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                prepared_request = {**prepared_request, **{'json': json_body}}
                process_response = api.process_response('set_product_stock', api.request(**prepared_request))
                # self.env['mp.base']._logger(self.marketplace, 'Product(s) updated', notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'activation':
            try:
                active_list = []
                inactive_list = []
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        if data['activate']:
                            active_list.append(int(data['product_obj'].mp_external_id))
                        else:
                            inactive_list.append(int(data['product_obj'].mp_external_id))
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        if data['activate']:
                            active_list.append(int(data['product_obj'].mp_product_id.mp_external_id))
                        else:
                            inactive_list.append(int(data['product_obj'].mp_product_id.mp_external_id))
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                if active_list:
                    prepared_request = api.build_request('set_product_active', **{
                        'params': params,
                        'json': {
                            'product_id': active_list
                        }
                    })
                    process_response = api.process_response('set_product_active', api.request(**prepared_request))
                    # self.env['mp.base']._logger(self.marketplace, 'Product(s) activated',
                    #                             notify=True, notif_sticky=False)
                if inactive_list:
                    prepared_request = api.build_request('set_product_inactive', **{
                        'params': params,
                        'json': {
                            'product_id': inactive_list
                        }
                    })
                    process_response = api.process_response('set_product_inactive', api.request(**prepared_request))
                    # self.env['mp.base']._logger(self.marketplace, 'Product(s) inactivated',
                    #                             notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        elif kw.get('mode') == 'detail':
            try:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                prepared_request = api.build_request('set_product_detail', **{
                    'params': params,
                    'json': {
                        'products': [{
                            'id': int(kw['data'].mp_product_id.mp_external_id),
                            'name': kw['data'].name,
                            'description': kw['data'].description,
                            'sku': kw['data'].sku,
                            'condition': kw['data'].condition,
                            'weight': kw['data'].weight,
                            'weight_unit': 'KG',
                            'dimension': {
                                'height': int(kw['data'].height),
                                'length': int(kw['data'].width),
                                'width': int(kw['data'].length),
                            },
                            'wholesale': [{
                                'min_qty': wholesale.min_qty,
                                'price': wholesale.price,
                            } for wholesale in kw['data'].wholesale_ids],
                            'pictures': [{
                                'file_path': '%s/png/%s/image/%s.png' % (base_url, image_id._name, image_id.id),
                            } for image_id in kw['data'].image_ids],
                        }]
                    }
                })
                mp_product_ids = kw['data'].mp_product_id.mapped('mp_external_id')
                process_response = api.process_response('set_product_detail', api.request(**prepared_request))
                # self.env['mp.base']._logger(self.marketplace, 'Product %s updated' %
                #                             (kw['data'].name), notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger(self.marketplace, e, notify=True, notif_sticky=False)
        self.tokopedia_get_products(**{'product_ids': mp_product_ids})

    def tokopedia_process_webhook_orders(self, limit=100, **kwargs):
        if not self.exists():
            if kwargs.get('id', False):
                rec = self.browse(kwargs.get('id'))
        else:
            rec = self

        # self.env['mp.base']._logger(rec.marketplace, 'START PROCESSING TOKOPEDIA WEBHOOK ORDER %s' %
        #                             (str(rec.id)), notify=False, notif_sticky=False)
        rec.ensure_one()
        webhook_order_obj = self.env['mp.webhook.order']

        order_not_process = webhook_order_obj.search(
            [('mp_account_id', '=', rec.id),
             ('is_process', '=', False),
             ('tp_order_status', 'in', ['220', '221'])], order='write_date', limit=limit)
        if order_not_process:
            order_not_process.is_process = True

        order_has_process = webhook_order_obj.search(
            [('mp_account_id', '=', rec.id),
             ('is_process', '=', False),
             ('tp_order_status', 'not in', ['220', '221'])], order='write_date', limit=limit)
        if order_has_process:
            order_has_process.is_process = True

        mp_invoice_number_in_process = [order.tp_order_id for order in order_not_process]
        mp_invoice_number_has_process = [order.tp_order_id for order in order_has_process]

        so_in_process = rec.tokopedia_get_sale_order(**{
            'mp_order_id': mp_invoice_number_in_process,
            'params': 'by_mp_invoice_number'})
        so_has_process = rec.tokopedia_get_sale_order(**{
            'mp_order_id': mp_invoice_number_has_process,
            'params': 'by_mp_invoice_number'})
        # self.env['mp.base']._logger(rec.marketplace, 'END PROCESSING TOKOPEDIA WEBHOOK ORDER %s' %
        #                             (str(rec.id)), notify=False, notif_sticky=False)

    @mp.tokopedia.capture_error
    def tokopedia_get_slash_price(self, **kw):
        self.ensure_one()
        params = {}
        _logger = self.env['mp.base']._logger
        mp_account_ctx = self.generate_context()
        mp_promotion_obj = self.env['mp.promotion.program']
        _notify = self.env['mp.base']._notify
        tp_account = self.tokopedia_get_account()
        tp_campaign = TokopediaCampaign(tp_account, api_version="v2")
        # _notify('info', 'Importing Slash Price from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

        slash_price = {}
        tp_discount_raws, tp_discount_sanitizeds = [], []
        tp_data_slash_price = tp_campaign.get_slash_price(shop_id=self.tp_shop_id.mp_external_id)
        i = 0
        allowed_promotion_status = [1, 2, 3]
        for discount in tp_data_slash_price:
            i += 1
            if discount['slash_price_status_id'] in allowed_promotion_status:
                # _logger(self.marketplace, 'discout: %s (%s - %s)' % (str(i), discount.get('start_date', ''), discount.get('end_date', '')),
                #         notify=False, notif_sticky=False)
                date_range = '%s - %s' % (discount['start_date'], discount['end_date'])
                if date_range not in slash_price:
                    if '+' in discount['start_date']:
                        iso_start_date = discount['start_date'][:-1].split('+')[0]
                        iso_end_date = discount['end_date'][:-1].split('+')[0]
                    else:
                        iso_start_date = discount['start_date'][:-1].split('.')[0]
                        iso_end_date = discount['end_date'][:-1].split('.')[0]

                    obj_start_date = self.env['mp.base'].datetime_convert_tz(datetime.fromisoformat(iso_start_date), 'Asia/Jakarta', 'Asia/Jakarta')
                    str_start_date = fields.Datetime.to_string(obj_start_date)

                    obj_end_date = self.env['mp.base'].datetime_convert_tz(datetime.fromisoformat(iso_end_date), 'Asia/Jakarta', 'Asia/Jakarta')
                    str_end_date = fields.Datetime.to_string(obj_end_date)

                    promotion_name = 'Tokopedia Slash Price %s - %s' % (str_start_date, str_end_date)
                    vals = {
                        'name': promotion_name,
                        'start_date': discount['start_date'],
                        'end_date': discount['end_date'],
                        'slash_price_status_id': discount['slash_price_status_id'],
                        'slash_price_line': [discount],
                        'promotion_type': 'discount',
                        'promotion_id': generate_id(promotion_name),
                        'is_uploaded': True,
                    }
                    slash_price[date_range] = vals
                else:
                    slash_price[date_range]['slash_price_line'].append(discount)

        if kw.get('params') == 'by_mp_promotion_id' and kw.get('mp_promotion_id', False):
            slas_price_raw = [slash_price[d] for d in slash_price if slash_price[d].get('promotion_id') == kw.get('mp_promotion_id')]
        else:
            slas_price_raw = [slash_price[d] for d in slash_price]
        tp_discount_data_raw, tp_discount_data_sanitized = mp_promotion_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=slas_price_raw)
        tp_discount_raws.extend(tp_discount_data_raw)
        tp_discount_sanitizeds.extend(tp_discount_data_sanitized)

        if tp_discount_raws and tp_discount_sanitizeds:
            check_existing_records_params = {
                'identifier_field': 'tp_promotion_id',
                'raw_data': tp_discount_raws,
                'mp_data': tp_discount_sanitizeds,
                'multi': isinstance(tp_discount_sanitizeds, list)
            }
            check_existing_records = mp_promotion_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_promotion_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    @mp.tokopedia.capture_error
    def tokopedia_get_bundle(self, **kw):
        self.ensure_one()
        params = {}
        mp_account_ctx = self.generate_context()
        mp_promotion_obj = self.env['mp.promotion.program']
        _notify = self.env['mp.base']._notify
        tp_account = self.tokopedia_get_account()
        tp_campaign = TokopediaCampaign(tp_account, api_version="v1")
        # _notify('info', 'Importing Bundle Campaign from {} is started... Please wait!'.format(self.marketplace.upper()),
        #         notif_sticky=False)

    @mp.tokopedia.capture_error
    def tokopedia_get_promotion(self, **kw):
        self.ensure_one()
        if kw.get('promotion_type') == 'discount':
            self.tokopedia_get_slash_price(**kw)
        elif kw.get('promotion_type') == 'bundle':
            self.tokopedia_get_bundle(**kw)
        else:
            self.tokopedia_get_slash_price(**kw)
            self.tokopedia_get_bundle(**kw)

        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }
