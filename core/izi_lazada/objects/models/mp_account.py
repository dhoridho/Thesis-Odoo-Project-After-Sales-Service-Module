# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from pytz import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
# from dict2xml import dict2xml

import json


from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_lazada.objects.utils.lazada.account import LazadaAccount
from odoo.addons.izi_lazada.objects.utils.lazada.seller import LazadaSeller
from odoo.addons.izi_lazada.objects.utils.lazada.logistic import LazadaLogistic
from odoo.addons.izi_lazada.objects.utils.lazada.product import LazadaProduct
from odoo.addons.izi_lazada.objects.utils.lazada.order import LazadaOrder
from odoo.addons.izi_lazada.objects.utils.lazada.api import LAZADA_COUNTRIES


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', False)],
    }

    lz_app_name = fields.Char(string="Lazada App Name", required_if_marketplace="lazada", states=READONLY_STATES)
    lz_app_key = fields.Char(string="Lazada App Key", required_if_marketplace="lazada", states=READONLY_STATES)
    lz_app_secret = fields.Char(string="Lazada App Secret", required_if_marketplace="lazada", states=READONLY_STATES)
    lz_country = fields.Selection(string="Lazada Country", selection=LAZADA_COUNTRIES, required_if_marketplace="lazada",
                                  states=READONLY_STATES)
    lz_country_user_ids = fields.One2many(related='mp_token_id.lz_country_user_ids', string='Lazada Country Users')
    lz_seller_id = fields.Many2one(comodel_name="mp.lazada.seller", string="Lazada Current Shop")
    lz_email_account = fields.Char(related='mp_token_id.lz_email_account')

    @api.model
    def lazada_get_account(self, **kwargs):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        credentials = {
            'host': kwargs.get('host', self.lz_country),
            'app_name': self.lz_app_name,
            'app_key': self.lz_app_key,
            'app_secret': self.lz_app_secret,
            'tid': self.lz_email_account,
            'country': self.lz_country,
            'mp_id': self.id,
            'code': kwargs.get('code', None),
            'refresh_token': kwargs.get('refresh_token', None),
            'access_token': kwargs.get('access_token', self.access_token),
            'base_url': base_url,
            'tz': self._context.get('tz', 'Asia/Jakarta')
        }
        lz_account = LazadaAccount(**credentials)
        return lz_account

    def lazada_authenticate(self):
        self.ensure_one()
        lz_account = self.lazada_get_account(host="oauth")
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': lz_account.get_auth_url()
        }

    def lazada_get_token(self, **kwargs):
        mp_token_obj = self.env['mp.token']
        lz_country_user_obj = self.env['mp.lazada.country.user']
        mp_account_ctx = self.generate_context()

        lz_account = self.lazada_get_account(host="auth", **kwargs)
        lz_response = lz_account.get_token()
        if lz_response.code == '0':
            raw_token = lz_response.body
            mp_token = mp_token_obj.lazada_create_token(self, raw_token)
        else:
            raise UserError(lz_response['message'])

        # process country user info
        user_country_list = json_digger(raw_token, 'country_user_info') or json_digger(
            raw_token, 'country_user_info_list')
        lz_user_country = [
            dict(user_info_raw,
                 **dict([('mp_token_id', mp_token.id if mp_token.exists() else None)]))
            for user_info_raw in user_country_list
        ]
        lz_token_data_raw, lz_token_data_sanitized = lz_country_user_obj.with_context(
            mp_account_ctx)._prepare_mapping_raw_data(raw_data=lz_user_country)

        check_existing_records_params = {
            'identifier_field': 'user_id',
            'raw_data': lz_token_data_raw,
            'mp_data': lz_token_data_sanitized,
            'multi': isinstance(lz_token_data_sanitized, list)
        }
        check_existing_records = lz_country_user_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        lz_country_user_obj.with_context(
            mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        tz = timezone(mp_account_ctx.get('tz', 'Asia/Jakarta'))
        time_now = str((datetime.now().astimezone(tz)).strftime("%Y-%m-%d %H:%M:%S"))
        auth_message = 'Congratulations, you have been successfully authenticated! from: %s' % (time_now)
        self.write({'state': 'authenticated',
                    'auth_message': auth_message})

        return mp_token

    def lazada_renew_token(self):
        self.ensure_one()
        current_token = False
        if self.mp_token_ids:
            current_token = self.mp_token_ids.sorted('expired_date', reverse=True)[0]
        if current_token:
            if current_token.refresh_token:
                request_params = {
                    'refresh_token': current_token.refresh_token,
                }
                try:
                    token = self.lazada_get_token(**request_params)
                    return token
                except Exception as e:
                    raise UserError(str(e.args[0]))

    def lazada_get_seller(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_lazada_seller_obj = self.env['mp.lazada.seller'].with_context(mp_account_ctx)
        if self.mp_token_id.state == 'valid':
            kwargs = {'access_token': self.mp_token_id.name}
            lz_account = self.lazada_get_account(host=self.lz_country, **kwargs)
            lz_seller = LazadaSeller(lz_account)
            _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                    notif_sticky=False)
            lz_response = lz_seller.get_seller_info()
            lz_data_raw, lz_data_sanitized = mp_lazada_seller_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=lz_response)
            check_existing_records_params = {
                'identifier_field': 'seller_id',
                'raw_data': lz_data_raw,
                'mp_data': lz_data_sanitized,
                'multi': isinstance(lz_data_sanitized, list)
            }
            check_existing_records = mp_lazada_seller_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            mp_lazada_seller_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def lazada_get_logistic(self):
        self.ensure_one()
        mp_account_ctx = self.generate_context()
        _notify = self.env['mp.base']._notify
        mp_lazada_logistic_obj = self.env['mp.lazada.logistic'].with_context(mp_account_ctx)
        if self.mp_token_id.state == 'valid':
            kwargs = {'access_token': self.mp_token_id.name}
            lz_account = self.lazada_get_account(host=self.lz_country, **kwargs)
            lz_logistic = LazadaLogistic(lz_account)
            _notify('info', 'Importing shop from {} is started... Please wait!'.format(self.marketplace.upper()),
                    notif_sticky=False)
            lz_response = lz_logistic.get_shipping_info()
            lz_data_raws, lz_data_sanitizeds = [], []
            for shipping in lz_response['shipment_providers']:
                lz_data_raw, lz_data_sanitized = mp_lazada_logistic_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=shipping)
                lz_data_raws.append(lz_data_raw)
                lz_data_sanitizeds.append(lz_data_sanitized)
            check_existing_records_params = {
                'identifier_field': 'name',
                'raw_data': lz_data_raws,
                'mp_data': lz_data_sanitizeds,
                'multi': isinstance(lz_data_sanitizeds, list)
            }
            check_existing_records = mp_lazada_logistic_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            mp_lazada_logistic_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def lazada_get_active_logistics(self):
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        self.lz_seller_id.with_context(mp_account_ctx).get_seller_logistics()

    def lazada_get_dependencies(self):
        self.ensure_one()
        self.lazada_get_seller()
        self.lazada_get_logistic()
        self.lazada_get_active_logistics()
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    def lazada_get_product(self, **kwargs):
        mp_product_obj = self.env['mp.product']
        mp_account_ctx = self.generate_context()
        self.ensure_one()
        _notify = self.env['mp.base']._notify
        if self.mp_token_id.state == 'valid':
            kwargs = {'access_token': self.mp_token_id.name}
            lz_account = self.lazada_get_account(host=self.lz_country, **kwargs)
            lz_product = LazadaProduct(lz_account)
            lz_response = lz_product.get_product_list()
            lz_data_raws, lz_data_sanitizeds = [], []
            for item in lz_response:
                # manipulation base data from lazada product for mapping
                item['attributes'].update({
                    'price': item['skus'][0]['price'],
                    'spesial_price': item['skus'][0]['special_price'],
                    'weight': item['skus'][0]['package_weight'],
                    'length': item['skus'][0]['package_length'],
                    'width': item['skus'][0]['package_width'],
                    'height': item['skus'][0]['package_height'],
                    'seller_sku': item['skus'][0]['SellerSku'],
                    'sku_id': item['skus'][0]['SkuId']
                })
                lz_data_raw, lz_data_sanitized = mp_product_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=item)
                lz_data_raws.append(lz_data_raw)
                lz_data_sanitizeds.append(lz_data_sanitized)

            check_existing_records_params = {
                'identifier_field': 'lz_item_id',
                'raw_data': lz_data_raws,
                'mp_data': lz_data_sanitizeds,
                'multi': isinstance(lz_data_sanitizeds, list)
            }
            check_existing_records = mp_product_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            mp_product_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def lazada_get_product_variant(self, **kw):
        mp_product_obj = self.env['mp.product']
        mp_product_variant_obj = self.env['mp.product.variant']
        self.ensure_one()

        mp_account_ctx = self.generate_context()

        if kw.get('product_ids'):
            product_ids = list(map(str, kw.get('product_ids')))
            mp_products = mp_product_obj.search(
                [('mp_external_id', 'in', product_ids),
                 ('mp_account_id', '=', self.id),
                 ('lz_has_variant', '=', True)])
        else:
            mp_products = mp_product_obj.search([('lz_has_variant', '=', True), ('mp_account_id', '=', self.id)])

        for mp_product in mp_products:
            variant_need_to_remove = []
            mp_product_raw = json.loads(mp_product.raw, strict=False)
            mp_product_variant_raw = mp_product_variant_obj.lz_generate_variant_data(mp_product_raw)
            mp_variant_exid_list = [variant_id['lz_variant_id'] for variant_id in mp_product_variant_raw]
            lz_data_raw, lz_data_sanitized = mp_product_variant_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=mp_product_variant_raw)

            check_existing_records_params = {
                'identifier_field': 'lz_variant_id',
                'raw_data': lz_data_raw,
                'mp_data': lz_data_sanitized,
                'multi': isinstance(lz_data_sanitized, list)
            }
            check_existing_records = mp_product_variant_obj.with_context(mp_account_ctx).check_existing_records(
                **check_existing_records_params)
            mp_product_variant_obj.with_context(mp_account_ctx).handle_result_check_existing_records(
                check_existing_records)

            for variant_obj in mp_product.mp_product_variant_ids:
                if int(variant_obj.lz_variant_id) not in mp_variant_exid_list:
                    variant_need_to_remove.append(variant_obj.lz_variant_id)

            mp_product.mp_product_variant_ids.filtered(lambda r: r.lz_variant_id in variant_need_to_remove).write({
                'active': False
            })

        # clean variant
        mp_products = mp_product_obj.search([('mp_product_variant_ids', '!=', False),
                                            ('lz_has_variant', '=', False),
                                            ('mp_account_id', '=', self.id)])
        for product in mp_products:
            for variant in product.mp_product_variant_ids:
                variant.active = False

    def lazada_get_products(self, **kwargs):
        self.ensure_one()
        self.lazada_get_product(**kwargs)
        self.lazada_get_product_variant(**kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications',
            'params': {
                'force_show_number': 1
            }
        }

    def lazada_get_orders_detail_test(self, **params):
        lz_data_raw = []
        lz_data_sanitized = []
        mp_account_ctx = self.generate_context()
        if params.get('mp_invoice_number'):
            for order_id in params.get('mp_invoice_number'):
                order_raw = self.env['ir.config_parameter'].sudo().get_param('mp.test.lz.order.raw')
                order_sanitized = self.env['ir.config_parameter'].sudo().get_param('mp.test.lz.order.sanitized')
                if not order_raw or not order_sanitized:
                    raise UserError('Set order template in mp.test.lz.order.raw in system parameter!')
                order_raw_vals = json.loads(order_raw)
                # lz_order_data_raw, lz_order_data_sanitized = self.env['sale.order'].with_context(
                #     mp_account_ctx)._prepare_mapping_raw_data(raw_data=order_raw_vals)
                order_sanitized_vals = eval(order_sanitized)
                order_raw_vals.update({
                    'order_number': order_id,
                    'invoice_number': order_id,
                })
                for index, order_detail in enumerate(order_raw_vals['order_line']):
                    order_detail.update({
                        'order_id': order_id,
                        'order_item_ids': '%s-%s' % (str(order_id), str(index))
                    })
                order_sanitized_vals.update({
                    'mp_external_id': order_id,
                    'lz_order_id': order_id,
                    'mp_invoice_number': order_id,
                })
                lz_data_raw.append(order_raw_vals)
                lz_data_sanitized.append(order_sanitized_vals)
        return lz_data_raw, lz_data_sanitized

    def lazada_get_sale_order(self, time_mode='update_time', **kwargs):
        mp_account_ctx = self.generate_context()
        if kwargs.get('force_update'):
            mp_account_ctx.update({'force_update': kwargs.get('force_update')})
        order_obj = self.env['sale.order'].with_context(dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        _logger = self.env['mp.base']._logger
        order_params = {}
        if self.mp_token_id.state == 'valid':
            account_params = {'access_token': self.mp_token_id.name}
            lz_account = self.lazada_get_account(host=self.lz_country, **account_params)
            lz_order = LazadaOrder(lz_account)
            _notify('info', 'Importing order from {} is started... Please wait!'.format(self.marketplace.upper()),
                    notif_sticky=False)

            skipped = 0
            force_update_ids = []
            lz_orders_by_mpexid = {}
            lz_order_raws = []
            lz_order_sanitizeds = []
            lz_orders = order_obj.search([('mp_account_id', '=', self.id)])
            for lz_order_rec in lz_orders:
                lz_orders_by_mpexid[lz_order_rec.mp_external_id] = lz_order_rec

            if kwargs.get('params') == 'by_date_range':
                order_params.update({
                    'from_date': kwargs.get('from_date'),
                    'to_date': kwargs.get('to_date'),
                    'limit': mp_account_ctx.get('order_limit'),
                    'time_mode': time_mode,
                })
                lz_order_list = lz_order.get_order_list(**order_params)
                order_list = []
                for lz_data_order in lz_order_list:
                    lz_order_id = str(lz_data_order['order_id'])
                    if lz_order_id in lz_orders_by_mpexid:
                        existing_order = lz_orders_by_mpexid[lz_order_id]
                        mp_status_changed = existing_order.lz_order_status != str(lz_data_order['statuses'][0])
                    else:
                        existing_order = False
                        mp_status_changed = False
                    no_existing_order = not existing_order
                    if no_existing_order or mp_status_changed or mp_account_ctx.get('force_update'):
                        if lz_data_order['statuses'][0] == 'unpaid':
                            if self.get_unpaid_orders:
                                order_list.append(lz_data_order)
                            else:
                                skipped += 1
                                continue
                        elif lz_data_order['statuses'][0] == 'canceled':
                            if self.get_cancelled_orders:
                                order_list.append(lz_data_order)
                            else:
                                skipped += 1
                                continue
                        else:
                            order_list.append(lz_data_order)

                        if existing_order and mp_account_ctx.get('force_update'):
                            force_update_ids.append(existing_order.id)

                if order_list:
                    lz_order_raw = lz_order.get_order_items(order_list)
                    for data in lz_order_raw:
                        lz_order_data_raw, lz_order_data_sanitized = order_obj.with_context(
                            mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
                        lz_order_raws.append(lz_order_data_raw)
                        lz_order_sanitizeds.append(lz_order_data_sanitized)

                _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
                    len(order_list), len(lz_order_list)
                ), notify=True, notif_sticky=False)
            else:
                # TODO : Get Single Order ID By Order ID
                lazada_order_id = kwargs.get('mp_invoice_number')
                if type(lazada_order_id) == str:
                    lazada_order_id = [lazada_order_id]

                # Check If Marketplace Test (mp.test)
                mp_test = self.env['ir.config_parameter'].sudo().get_param('mp.test')
                if mp_test:
                    lz_data_raw, lz_data_sanitized = self.lazada_get_orders_detail_test(**kwargs)
                    lz_order_raws.extend(lz_data_raw)
                    lz_order_sanitizeds.extend(lz_data_sanitized)
                else:
                    lz_orders_detail = lz_order.get_order(order_ids=lazada_order_id)
                    lz_order_raw = lz_order.get_order_items(lz_orders_detail)
                    for data in lz_order_raw:
                        lz_order_data_raw, lz_order_data_sanitized = order_obj.with_context(
                            mp_account_ctx)._prepare_mapping_raw_data(raw_data=data)
                        lz_order_raws.append(lz_order_data_raw)
                        lz_order_sanitizeds.append(lz_order_data_sanitized)
                    _logger(self.marketplace, 'Processed %s order(s) from %s of total orders imported!' % (
                        len(lz_order_raw), len(lz_order_raw)
                    ), notify=True, notif_sticky=False)

            if force_update_ids:
                order_obj = order_obj.with_context(dict(order_obj._context.copy(), **{
                    'force_update_ids': force_update_ids
                }))

            if lz_order_raws and lz_order_sanitizeds:
                check_existing_records_params = {
                    'identifier_field': 'lz_order_id',
                    'raw_data': lz_order_raws,
                    'mp_data': lz_order_sanitizeds,
                    'multi': isinstance(lz_order_sanitizeds, list)
                }
                check_existing_records = order_obj.with_context(mp_account_ctx).check_existing_records(
                    **check_existing_records_params)
                order_obj.with_context(mp_account_ctx).handle_result_check_existing_records(check_existing_records)
            else:
                _logger(self.marketplace, 'There is no update, skipped %s order(s)!' % skipped, notify=True,
                        notif_sticky=False)

    def lazada_get_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        time_mode = kwargs.get('time_mode', 'update_time')
        if 'time_mode' in kwargs:
            kwargs.pop('time_mode')
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
        rec.lazada_get_sale_order(time_mode=time_mode, **kwargs)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def lazada_get_saldo_history(self, **kwargs):
        mp_account_ctx = self.generate_context()
        account_bank_statement_obj = self.env['account.bank.statement'].with_context(
            dict(mp_account_ctx, **self._context.copy()))
        _notify = self.env['mp.base']._notify
        mp_account_ctx.update({
            'force_update': True
        })
        self.ensure_one()

        _notify('info', 'Importing order wallet from {} is started... Please wait!'.format(self.marketplace.upper()),
                notif_sticky=False)
        from_date = kwargs.get('from_date')
        to_date = kwargs.get('to_date')
        total_days = (to_date - from_date).days
        bank_statement_raw = []
        if total_days == 0:
            from_date_str = (kwargs.get('from_date') + relativedelta(hours=7)).strftime("%Y/%m/%d")
            to_date_str = (kwargs.get('to_date')+relativedelta(hours=7)).strftime("%Y/%m/%d")
            bank_statement_raw.append({
                'name': 'Lazada Saldo: %s' % ((from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
                'date': (from_date + relativedelta(hours=7)).strftime("%Y/%m/%d"),
                'journal_id': self.wallet_journal_id.id,
                'mp_start_date': from_date_str,
                'mp_end_date': to_date_str
            })
        else:
            for index in range(0, total_days):
                new_from_date = from_date + relativedelta(days=index)
                new_to_date = from_date + relativedelta(days=index)
                bank_statement_raw.append({
                    'name': 'Lazada Saldo: %s' % ((new_from_date + relativedelta(hours=7)).strftime("%Y/%m/%d")),
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

    def lazada_auto_reconcile(self, **kwargs):
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
                    _logger(self.marketplace, 'RECONCILE PROCESS FOR BANK STATEMENTS %s' % (bank_statement.name),
                            notify=True,
                            notif_sticky=False)

                    # New Method For Reconcile
                    bank_statement.process_bank_statement_reconciliation()

    def lazada_get_orders_wallet(self, **kwargs):
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
        bank_statement = rec.lazada_get_saldo_history(**kwargs)
        if kwargs.get('mode') in ['reconcile_only', 'both']:
            bank_statement_list = [data['name'] for data in bank_statement]
            auto_rec_param = {'bank_statement_list': bank_statement_list}
            rec.lazada_auto_reconcile(**auto_rec_param)
        return {
            'type': 'ir.actions.client',
            'tag': 'close_notifications'
        }

    def lazada_set_product(self, **kw):
        self.ensure_one()
        mp_product_ids = []
        account_params = {'access_token': self.mp_token_id.name}
        lz_account = self.lazada_get_account(host=self.lz_country, **account_params)
        lz_product = LazadaProduct(lz_account)
        base_payload = {
            'Request': {
                'Product': {
                    'Skus': {
                        'Sku': []
                    }
                }
            }
        }
        if kw.get('mode') == 'stock_only':
            try:
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        sku_dict = {
                            'ItemId': str(data['product_obj'].mp_external_id),
                            'SkuId': str(data['product_obj'].lz_sku_id),
                            'SellerSku': data['product_obj'].default_code,
                            'Quantity': int(data['stock'])
                        }
                        sku = base_payload['Request']['Product']['Skus']['Sku']
                        sku.append(sku_dict)
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        sku_dict = {
                            'ItemId': str(data['product_obj'].mp_product_id.mp_external_id),
                            'SkuId': str(data['product_obj'].lz_variant_id),
                            'SellerSku': data['product_obj'].default_code,
                            'Quantity': int(data['stock'])
                        }
                        sku = base_payload['Request']['Product']['Skus']['Sku']
                        sku.append(sku_dict)
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                response = lz_product.update_product_price_qty(base_payload)
            except Exception as e:
                pass
        if kw.get('mode') == 'price_only':
            try:
                for data in kw.get('data', []):
                    if data['product_obj']._name == 'mp.product':
                        sku_dict = {
                            'ItemId': str(data['product_obj'].mp_external_id),
                            'SkuId': str(data['product_obj'].lz_sku_id),
                            'SellerSku': data['product_obj'].default_code,
                            'Price': float(data['price'])
                        }
                        sku = base_payload['Request']['Product']['Skus']['Sku']
                        sku.append(sku_dict)
                        mp_product_ids.append(int(data['product_obj'].mp_external_id))
                    elif data['product_obj']._name == 'mp.product.variant':
                        sku_dict = {
                            'ItemId': str(data['product_obj'].mp_product_id.mp_external_id),
                            'SkuId': str(data['product_obj'].lz_variant_id),
                            'SellerSku': data['product_obj'].default_code,
                            'Price': float(data['price'])
                        }
                        sku = base_payload['Request']['Product']['Skus']['Sku']
                        sku.append(sku_dict)
                        mp_product_ids.append(int(data['product_obj'].mp_product_id.mp_external_id))
                response = lz_product.update_product_price_qty(base_payload)
            except Exception as e:
                pass
        if kw.get('mode') == 'activation':
            pass
        if kw.get('mode') == 'detail':
            pass

    def lazada_process_webhook_orders(self, limit=100, **kwargs):

        if not self.exists():
            if kwargs.get('id', False):
                rec = self.browse(kwargs.get('id'))
        else:
            rec = self
        self.env['mp.base']._logger(rec.marketplace, 'START PROCESSING LAZADA WEBHOOK ORDER %s' %
                                    (str(rec.id)), notify=False, notif_sticky=False)
        total_rec = limit
        rec.ensure_one()
        query = '''
            SELECT
                mp_invoice_number
            FROM mp_webhook_order mwo
            WHERE mwo.mp_account_id = %s
            AND mwo.is_process = false
            AND mwo.lz_order_status in ('pending')
            GROUP BY mp_invoice_number
            limit %s
        ''' % (str(rec.id), str(total_rec))
        self.env.cr.execute(query)
        order_not_process = self.env.cr.fetchall()

        mp_invoice_number_in_process = [order[0] for order in order_not_process]

        total_rec = total_rec+(limit-len(order_not_process))
        query = '''
            SELECT
                mp_invoice_number
            FROM mp_webhook_order mwo
            WHERE mwo.mp_account_id = %s
            AND mwo.is_process = false
            AND mwo.lz_order_status not in ('unpaid', 'pending')
            GROUP BY mp_invoice_number
            limit %s
        ''' % (str(rec.id), str(total_rec))
        self.env.cr.execute(query)
        order_has_process = self.env.cr.fetchall()

        mp_invoice_number_has_process = [order[0] for order in order_has_process]
        all_orders = mp_invoice_number_in_process+mp_invoice_number_has_process

        if all_orders:
            query = '''
                UPDATE mp_webhook_order
                SET is_process = true
                WHERE mp_invoice_number in %s
            ''' % (str(tuple(all_orders)))
            self.env.cr.execute(query)

        so_in_process = rec.lazada_get_sale_order(**{
            'mp_invoice_number': mp_invoice_number_in_process,
            'params': 'by_mp_invoice_number'})
        so_has_process = rec.lazada_get_sale_order(**{
            'mp_invoice_number': mp_invoice_number_has_process,
            'params': 'by_mp_invoice_number'})
        self.env['mp.base']._logger(rec.marketplace, 'END PROCESSING LAZADA WEBHOOK ORDER %s' %
                                    (str(rec.id)), notify=False, notif_sticky=False)
