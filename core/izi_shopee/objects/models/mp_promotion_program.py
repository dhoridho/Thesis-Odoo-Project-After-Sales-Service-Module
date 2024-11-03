# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
import time
import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_shopee.objects.utils.shopee.account import ShopeeAccount
from odoo.addons.izi_shopee.objects.utils.shopee.promotion import ShopeePromotion


class MPPromotionProgram(models.Model):
    _inherit = 'mp.promotion.program'

    _SP_PROMOTION_STATUS = [
        ('ongoing', 'ONGOING'),
        ('expired', 'EXPIRED'),
        ('upcoming', 'UPCOMING'),
    ]

    _VOUCHER_TYPE = [
        ("1", "Shop Voucher"),
        ("2", "Product Vocuher")
    ]

    _VOUCHER_REWARD_TYPE = [
        ("1", "Fix Amount Voucher"),
        ("2", "Discount Percentage"),
        ("3", "Coin Cashback Voucher")
    ]

    _BUNDLE_RULE_TYPE = [
        ('1', "Fixed Amount"),
        ('2', "Discount Percentage"),
        ('3', "Discount Value")
    ]

    _ADDON_DEAL_TYPE = [
        ("0", "Add on Discount"),
        ("1", "Gift with Min Spend")
    ]

    READONLY_STATES = {
        'wait': [('readonly', True)],
        'run': [('readonly', True)],
        'done': [('readonly', True)],
    }

    sp_promotion_status = fields.Selection(selection=_SP_PROMOTION_STATUS, string='Shopee Promotion Status')
    sp_promotion_id = fields.Char(string='Shopee Promotion ID', index=True)

    # Voucher Field
    sp_base_voucher_code = fields.Char(string='Base Voucher Code', size=4, readonly=True)
    sp_voucher_code = fields.Char(string='Voucher Code', size=5, states=READONLY_STATES)
    sp_voucher_type = fields.Selection(selection=_VOUCHER_TYPE, string='Voucher Type', states=READONLY_STATES)
    sp_reward_type = fields.Selection(selection=_VOUCHER_REWARD_TYPE, string='Reward Type', states=READONLY_STATES)
    sp_usage_quantity = fields.Integer(string='Usage Quantity')
    sp_min_basket_price = fields.Float(string='Min. Basket Price')
    sp_discount_amount = fields.Float(string='Discount Amount')
    sp_discount_percentage = fields.Integer(string='Voucher Discount Percentage')
    sp_set_maximum = fields.Boolean(string='Set the Maximum Discount ?')
    sp_max_price = fields.Float(string='Max Amount of Discount')
    sp_display_channel_list = fields.Many2many(comodel_name='mp.shopee.voucher.channel', string='Voucher Display')
    sp_voucher_item_list = fields.One2many(
        comodel_name='mp.shopee.voucher.product', inverse_name='promotion_id', string='Vocuher Product List')

    # Bundle Field
    sp_bundle_rule_type = fields.Selection(selection=_BUNDLE_RULE_TYPE,
                                           string='Shopee Bundle Type', states=READONLY_STATES)
    sp_bundle_min_amount = fields.Integer(string='Minimal Qty Amount',
                                          help='The quantity of items that need buyer to combine purchased', default=2)
    sp_bundle_purchase_limit = fields.Integer(string='Purchase Limit', default=1,
                                              help='Maximum number of bundle deals that can be bought by a buyer.')
    sp_bundle_discount_value = fields.Float(
        string='Discount Value', help='The deducted price when when buying a bundle deal.', default=0)
    sp_bundle_fix_price = fields.Float(
        string='Fix Price', help='The amount of the buyer needs to spend to purchase a bundle deal.', default=0)
    sp_bundle_discount_percentage = fields.Float(
        string='Bundle Discount Percentage', help='The discount that the buyer can get when buying a bundle deal.', default=0)
    sp_bundle_item_list = fields.One2many(
        comodel_name='mp.shopee.bundle.product', inverse_name='promotion_id', string='Bundle Product List')

    # Add On Deal Field
    sp_addon_deal_type = fields.Selection(selection=_ADDON_DEAL_TYPE, string='Promo Type', states=READONLY_STATES)
    sp_addon_purchase_limit = fields.Integer(string='Product Purchase Limit', default=0,
                                             help='Maximum number of add on deals that can be bought by a buyer.')
    sp_addon_purchase_min_spend = fields.Float(string='Purchase Min Spend', default=0,
                                               help='The minimum purchase amount that needs to be met to buy the gift with min.Spend.')
    sp_addon_per_gift_num = fields.Integer(string='Gift Number', default=0,
                                           help='Number of gifts that buyers can get')
    sp_addon_main_item_ids = fields.One2many(
        comodel_name='mp.shopee.addon.main.product', inverse_name='promotion_id', string='Addon Main Product')
    sp_addon_sub_item_ids = fields.One2many(
        comodel_name='mp.shopee.addon.sub.product', inverse_name='promotion_id', string='Addon Sub Product')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'sp_promotion_id': ('base_info/promotion_id', None),
            'mp_external_id': ('base_info/promotion_id', None),
            'sp_promotion_status': ('base_info/status', None),
            'name': ('base_info/name', lambda env, r: str(r) if r else None),
            'is_uploaded': ('base_info/is_uploaded', None),

            # voucher fields
            'sp_voucher_type': ('voucher/voucher_type', lambda env, r: str(r) if r else None),
            'sp_reward_type': ('voucher/reward_type', lambda env, r: str(r) if r else None),
            'sp_usage_quantity': ('voucher/usage_quantity', None),
            'sp_min_basket_price': ('voucher/min_basket_price', None),
            'sp_discount_amount': ('voucher/discount_amount', None),
            'sp_discount_percentage': ('voucher/percentage', None),
            'sp_max_price': ('voucher/max_price', None),
            'sp_set_maximum': ('voucher/max_price', lambda env, r: True if r else False),

            # bundle deal fields
            'sp_bundle_rule_type': ('bundle/rule_type', lambda env, r: str(r) if r else None),
            'sp_bundle_min_amount': ('bundle/min_amount', None),
            'sp_bundle_purchase_limit': ('bundle/purchase_limit', None),
            'sp_bundle_discount_value': ('bundle/discount_value', None),
            'sp_bundle_fix_price': ('bundle/fix_price', None),
            'sp_bundle_discount_percentage': ('bundle/discount_percentage', None),

            # addon deak fields
            'sp_addon_purchase_limit': ('addon/promotion_purchase_limit', None),
            'sp_addon_purchase_min_spend': ('addon/purchase_min_spend', None),
            'sp_addon_per_gift_num': ('addon/per_gift_num', None),
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _handle_promotion_state(env, data):
            if data:
                if data == 'upcoming':
                    return 'wait'
                elif data == 'ongoing':
                    return 'run'
                elif data == 'expired':
                    return 'stop'
            return None

        def _handle_promotion_type(env, data):
            if data:
                domain = [
                    ('marketplace', '=', 'shopee'),
                    ('code', '=', data)
                ]
                mp_promotion_type = env['mp.promotion.program.type'].search(domain, limit=1)
                if mp_promotion_type:
                    return mp_promotion_type.id
                else:
                    return None
            return None

        def _handle_base_voucher_code(env, data):
            if data:
                return data[:4]
            return None

        def _handle_voucher_code(env, data):
            if data:
                return data[4:]
            return None

        def _handle_voucher_channel_list(env, data):
            if data:
                mp_voucher_channel_obj = env['mp.shopee.voucher.channel']
                records = mp_voucher_channel_obj.search([('code', 'in', data)])
                if records:
                    return [(6, 0, [rec.id for rec in records])]
                else:
                    return None
            return None

        def _handle_add_on_deal_type(env, data):
            if data == 0 or data == 1:
                return str(data)
            else:
                return None

        mp_field_mapping.update({
            'date_start': ('base_info/start_time', _convert_timestamp_to_datetime),
            'date_end': ('base_info/end_time', _convert_timestamp_to_datetime),
            'state': ('base_info/status', _handle_promotion_state),
            'promotion_type': ('base_info/type', _handle_promotion_type),

            # voucher fields
            'sp_base_voucher_code': ('voucher/voucher_code', _handle_base_voucher_code),
            'sp_voucher_code': ('voucher/voucher_code', _handle_voucher_code),
            'sp_display_channel_list': ('voucher/display_channel_list', _handle_voucher_channel_list),

            # addon fields
            'sp_addon_deal_type': ('addon/promotion_type', _handle_add_on_deal_type),


        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgram, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        records = super(MPPromotionProgram, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'shopee':
            records = self.shopee_process_promotion_lines(mp_account, records)
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(MPPromotionProgram, self)._finish_update_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'shopee':
            records = self.shopee_process_promotion_lines(mp_account, records)
        return records

    def shopee_process_promotion_lines(self, mp_account, records):
        mp_account_ctx = mp_account.generate_context()
        _logger = self.env['mp.base']._logger

        for record in records:
            sp_promotion_line_raws, sp_promotion_line_sanitizeds = [], []
            sp_order_raw = json.loads(record.raw, strict=False)
            now = datetime.now()
            if record.date_start < now and record.date_end > now:
                record.write({
                    'sp_promotion_status': 'ongoing',
                    'state': 'run'
                })
            elif record.date_start > now and record.date_end > now:
                record.write({
                    'sp_promotion_status': 'upcoming',
                    'state': 'wait'
                })
            else:
                record.write({
                    'sp_promotion_status': 'expired',
                    'state': 'stop'
                })

            if record.promotion_type.code == 'discount':
                mp_promotion_program_line_obj = self.env['mp.promotion.program.line']
                item_list = sp_order_raw['discount']['item_list']
                new_item_list = []
                for item in item_list:
                    if 'model_list' in item:
                        if item['model_list']:
                            for model in item['model_list']:
                                vals = {
                                    'item_id': item['item_id'],
                                    'model_id': model['model_id'],
                                    'item_name': '%s (%s)' % (item['item_name'], model['model_name']),
                                    'purchase_limit': item['purchase_limit'],
                                    'item_promotion_price': model['model_promotion_price'],
                                    'item_original_price': model['model_original_price'],
                                    'item_promotion_stock': model['model_promotion_stock'],
                                    'normal_stock': model['model_normal_stock']
                                }
                                new_item_list.append(vals)
                    else:
                        new_item_list.append(item)

                sp_discount_line = [
                    # Insert promotion into item_list
                    dict(sp_discount_line_raw,
                         **dict([('promotion_id', record.id)]),
                         **dict([('price_mode', 'fixed')]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for sp_discount_line_raw in new_item_list
                ]
                sp_data_raw, sp_data_sanitized = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_discount_line)
                sp_promotion_line_raws.extend(sp_data_raw)
                sp_promotion_line_sanitizeds.extend(sp_data_sanitized)

                def identify_promotion_line(record_obj, values):
                    return record_obj.search([('promotion_id', '=', values['promotion_id']),
                                              ('mp_product_name', '=', values['mp_product_name'])], limit=1)

                check_existing_records_params = {
                    'identifier_method': identify_promotion_line,
                    'raw_data': sp_promotion_line_raws,
                    'mp_data': sp_promotion_line_sanitizeds,
                    'multi': isinstance(sp_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

            elif record.promotion_type.code == 'voucher':
                mp_voucher_product_obj = self.env['mp.shopee.voucher.product']

                if record.sp_voucher_type == '2':
                    item_list = sp_order_raw['voucher']['item_id_list']
                    sp_voucher_line = [
                        # Insert promotion into item_list
                        dict(**dict([('promotion_id', record.id)]),
                             **dict([('mp_product_id', sp_voucher_line_raw)]),
                             **dict([('mp_product_exid', sp_voucher_line_raw)]),
                             **dict([('mp_promotion_exid', record.mp_external_id)]))
                        for sp_voucher_line_raw in item_list
                    ]
                    sp_data_raw, sp_data_sanitized = mp_voucher_product_obj.with_context(
                        mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_voucher_line)
                    sp_promotion_line_raws.extend(sp_data_raw)
                    sp_promotion_line_sanitizeds.extend(sp_data_sanitized)

                    def identify_promotion_line(record_obj, values):
                        return record_obj.search([('promotion_id', '=', values['promotion_id']),
                                                  ('mp_product_exid', '=', values['mp_product_exid'])], limit=1)

                    check_existing_records_params = {
                        'identifier_method': identify_promotion_line,
                        'raw_data': sp_promotion_line_raws,
                        'mp_data': sp_promotion_line_sanitizeds,
                        'multi': isinstance(sp_promotion_line_sanitizeds, list)
                    }
                    check_existing_records = mp_voucher_product_obj.with_context(
                        mp_account_ctx).check_existing_records(**check_existing_records_params)
                    mp_voucher_product_obj.with_context(
                        mp_account_ctx).handle_result_check_existing_records(check_existing_records)

            elif record.promotion_type.code == 'bundle':
                mp_bundle_product_obj = self.env['mp.shopee.bundle.product']
                item_list = sp_order_raw['bundle']['item_list']
                sp_bundle_line = [
                    # Insert promotion into item_list
                    dict(sp_bundle_line_raw,
                         ** dict([('promotion_id', record.id)]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for sp_bundle_line_raw in item_list
                ]
                sp_data_raw, sp_data_sanitized = mp_bundle_product_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_bundle_line)
                sp_promotion_line_raws.extend(sp_data_raw)
                sp_promotion_line_sanitizeds.extend(sp_data_sanitized)

                def identify_promotion_line(record_obj, values):
                    return record_obj.search([('promotion_id', '=', values['promotion_id']),
                                              ('mp_product_exid', '=', values['mp_product_exid'])], limit=1)

                check_existing_records_params = {
                    'identifier_method': identify_promotion_line,
                    'raw_data': sp_promotion_line_raws,
                    'mp_data': sp_promotion_line_sanitizeds,
                    'multi': isinstance(sp_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_bundle_product_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_bundle_product_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

            elif record.promotion_type.code == 'addon':
                mp_addon_main_product_obj = self.env['mp.shopee.addon.main.product']
                mp_addon_sub_product_obj = self.env['mp.shopee.addon.sub.product']

                # process main product first
                main_item_list = sp_order_raw['addon']['main_item']
                sp_addon_main_line = [
                    # Insert promotion into item_list
                    dict(sp_addon_main_line_raw,
                         ** dict([('promotion_id', record.id)]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for sp_addon_main_line_raw in main_item_list
                ]
                sp_data_raw, sp_data_sanitized = mp_addon_main_product_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_addon_main_line)
                sp_promotion_line_raws.extend(sp_data_raw)
                sp_promotion_line_sanitizeds.extend(sp_data_sanitized)

                def identify_promotion_main_line(record_obj, values):
                    return record_obj.search([('promotion_id', '=', values['promotion_id']),
                                              ('mp_product_exid', '=', values['mp_product_exid'])], limit=1)

                check_existing_records_params = {
                    'identifier_method': identify_promotion_main_line,
                    'raw_data': sp_promotion_line_raws,
                    'mp_data': sp_promotion_line_sanitizeds,
                    'multi': isinstance(sp_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_addon_main_product_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_addon_main_product_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

                # clear after processing main product
                sp_promotion_line_raws.clear()
                sp_promotion_line_sanitizeds.clear()

                # process sub product first
                sub_item_list = sp_order_raw['addon']['sub_item']

                # grouping item_id and model_id in 1 key 'item_info'
                list_item_field = ['item_id', 'model_id']
                for item in sub_item_list:
                    item['item_info'] = dict([(key, item[key]) for key in list_item_field if key in item])

                sp_addon_sub_line = [
                    # Insert promotion into item_list
                    dict(sp_addon_sub_line_raw,
                         **dict([('promotion_id', record.id)]),
                         **dict([('price_mode', 'fixed')]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for sp_addon_sub_line_raw in sub_item_list
                ]
                sp_data_raw, sp_data_sanitized = mp_addon_sub_product_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_addon_sub_line)
                sp_promotion_line_raws.extend(sp_data_raw)
                sp_promotion_line_sanitizeds.extend(sp_data_sanitized)

                def identify_promotion_sub_line(record_obj, values):
                    return record_obj.search([('promotion_id', '=', values['promotion_id']),
                                              ('mp_product_exid', '=', values['mp_product_exid'])], limit=1)

                check_existing_records_params = {
                    'identifier_method': identify_promotion_sub_line,
                    'raw_data': sp_promotion_line_raws,
                    'mp_data': sp_promotion_line_sanitizeds,
                    'multi': isinstance(sp_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_addon_sub_product_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_addon_sub_product_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    def shopee_generate_item_list(self):
        item_list_by_exid = {}
        if not self.product_discount_ids:
            raise UserError('Product discount not found.')
        for product_disc in self.product_discount_ids:
            mp_product_exid = product_disc.mp_product_id.mp_external_id
            if mp_product_exid not in item_list_by_exid:
                body_item = {
                    'item_id': int(product_disc.mp_product_id.mp_external_id),
                    'model_list': []
                }
                if product_disc.mp_product_variant_id:
                    model_data = {
                        'model_id':  int(product_disc.mp_product_variant_id.mp_external_id),
                        'model_promotion_price': product_disc.final_item_price,
                        'model_promotion_stock': product_disc.item_stock
                    }
                    body_item['model_list'].append(model_data)
                else:
                    body_item.update({
                        'item_promotion_price': product_disc.final_item_price,
                        'item_promotion_stock': product_disc.item_stock
                    })
                body_item['purchase_limit'] = product_disc.purchase_limit
                item_list_by_exid[mp_product_exid] = body_item
            else:
                body_item = item_list_by_exid[mp_product_exid]
                model_data = {
                    'model_id':  int(product_disc.mp_product_variant_id.mp_external_id),
                    'model_promotion_price': product_disc.final_item_price,
                    'model_promotion_stock': product_disc.item_stock
                }
                body_item['model_list'].append(model_data)

        return item_list_by_exid

    @mp.shopee.capture_error
    def shopee_upload_promotion(self):
        sp_account = False
        upload_promotion = False
        for promotion in self:
            if not promotion.promotion_type:
                raise UserError('Promotion type not found.')
            if promotion.is_uploaded:
                promotion.shopee_update_promotion()

            datetime_now = datetime.now() + timedelta(minutes=10)
            if promotion.date_start < datetime_now:
                raise UserError('Promotion start date is set at least 10 minutes from time now.')

            if promotion.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': promotion.mp_account_id.mp_token_id.name}
                sp_account = promotion.mp_account_id.shopee_get_account(**params)
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

            if sp_account:
                sp_discount = ShopeePromotion(sp_account)
                add_promotion_params = {
                    'promotion_name': promotion.name,
                    'start_time': int(datetime.timestamp(promotion.date_start)),
                    'end_time': int(datetime.timestamp(promotion.date_end))
                }
                if promotion.code == 'discount':
                    # upload discount
                    discount_data = sp_discount.add_discount(**add_promotion_params)
                    if discount_data:
                        promotion.write({
                            'mp_external_id': str(discount_data.get('discount_id')),
                            'is_uploaded': True,
                            'state': 'wait'
                        })

                        # upload discount item
                        item_list_by_exid = promotion.shopee_generate_item_list()

                        add_discount_item_params = {
                            'discount_id': promotion.mp_external_id,
                            'item_list': [],
                        }
                        for item in item_list_by_exid:
                            add_discount_item_params['item_list'].append(item_list_by_exid[item])
                        discount_item_data = sp_discount.add_discount_item(**add_discount_item_params)
                        if discount_item_data:
                            if 'error_list' in discount_item_data and discount_item_data['error_list']:
                                raise UserError(discount_item_data['error_list'][0]['fail_message'])
                            else:
                                upload_promotion = True

                elif promotion.code == 'voucher':
                    add_promotion_params.update({
                        'voucher_code': promotion.sp_voucher_code,
                        'voucher_type': int(promotion.sp_voucher_type),
                        'reward_type': int(promotion.sp_reward_type),
                        'usage_quantity': promotion.sp_usage_quantity,
                        'min_basket_price': promotion.sp_min_basket_price,
                        'display_channel_list': promotion.sp_display_channel_list.mapped('code')
                    })
                    if promotion.sp_reward_type == '1':
                        add_promotion_params.update({
                            'discount_amount': promotion.sp_discount_amount,
                        })
                    else:
                        add_promotion_params.update({
                            'percentage': int(promotion.sp_discount_percentage),
                            'max_price': promotion.sp_max_price,
                        })

                    if promotion.sp_voucher_type == '2':
                        item_list = [int(item.mp_product_id.mp_external_id) for item in promotion.sp_voucher_item_list]
                        add_promotion_params.update({
                            'item_id_list': item_list,
                        })

                    # upload voucher
                    voucher_data = sp_discount.add_voucher(**add_promotion_params)
                    if voucher_data:
                        upload_promotion = True
                        promotion.write({
                            'mp_external_id': str(voucher_data.get('voucher_id')),
                            'is_uploaded': True,
                            'state': 'wait'
                        })

                elif promotion.code == 'bundle':
                    add_promotion_params.update({
                        'rule_type': int(promotion.sp_bundle_rule_type),
                        'min_amount': promotion.sp_bundle_min_amount,
                        'purchase_limit': promotion.sp_bundle_purchase_limit,
                        'fix_price': promotion.sp_bundle_fix_price,
                        'discount_percentage': int(promotion.sp_bundle_discount_percentage),
                        'discount_value': promotion.sp_bundle_discount_value,
                    })
                    # upload discount
                    bundle_data = sp_discount.add_bundle(**add_promotion_params)
                    if bundle_data:
                        promotion.write({
                            'mp_external_id': str(bundle_data.get('bundle_deal_id')),
                            'is_uploaded': True,
                            'state': 'wait'
                        })

                        # upload bundle item
                        add_bundle_item_params = {
                            'bundle_deal_id': promotion.mp_external_id,
                            'item_list': [],
                        }
                        for item in promotion.sp_bundle_item_list:
                            bundle_item = {
                                'item_id': item.mp_product_id.mp_external_id,
                                'status': 1
                            }
                            add_bundle_item_params['item_list'].append(bundle_item)
                        bundle_item_data = sp_discount.add_bundle_item(**add_bundle_item_params)

                        if bundle_item_data.get('error_list', False):
                            raise UserError(bundle_item_data['error_list'][0]['fail_message'])
                        else:
                            upload_promotion = True

                elif promotion.code == 'addon':
                    add_promotion_params.update({
                        'promotion_type': int(promotion.sp_bundle_rule_type),
                    })
                    if promotion.sp_addon_purchase_limit != 0:
                        add_promotion_params.update({
                            'promotion_purchase_limit': promotion.sp_addon_purchase_limit
                        })
                    if promotion.sp_addon_purchase_min_spend != 0:
                        add_promotion_params.update({
                            'purchase_min_spend': promotion.sp_addon_purchase_min_spend
                        })
                    if promotion.sp_addon_per_gift_num != 0:
                        add_promotion_params.update({
                            'per_gift_num': promotion.sp_addon_per_gift_num
                        })

                    # upload addon deak
                    addon_data = sp_discount.add_addon(**add_promotion_params)
                    if addon_data:
                        promotion.write({
                            'mp_external_id': str(addon_data.get('add_on_deal_id')),
                            'is_uploaded': True,
                            'state': 'wait'
                        })
                        self.env.cr.commit()
                        # upload addon main item
                        add_addon_main_item_params = {
                            'add_on_deal_id': int(promotion.mp_external_id),
                            'main_item_list': [],
                        }
                        for item in promotion.sp_addon_main_item_ids:
                            addon_main_item = {
                                'item_id': item.mp_product_id.mp_external_id,
                                'status': 1
                            }
                            add_addon_main_item_params['main_item_list'].append(addon_main_item)
                        addon_main_item_data = sp_discount.add_addon_main_item(**add_addon_main_item_params)

                        # upload addon sub item
                        add_addon_sub_item_params = {
                            'add_on_deal_id': int(promotion.mp_external_id),
                            'sub_item_list': [],
                        }
                        for item in promotion.sp_addon_sub_item_ids:
                            addon_sub_item = {
                                'item_id': int(item.mp_product_id.mp_external_id),
                                'status': 1,
                                'sub_item_input_price': item.final_item_price,
                            }
                            if item.mp_product_variant_id:
                                addon_sub_item.update({
                                    'model_id': int(item.mp_product_variant_id.mp_external_id)
                                })
                            if item.purchase_limit != 0:
                                addon_sub_item.update({
                                    'sub_item_limit': int(item.purchase_limit)
                                })
                            add_addon_sub_item_params['sub_item_list'].append(addon_sub_item)

                        addon_sub_item_data = sp_discount.add_addon_sub_item(**add_addon_sub_item_params)

                if upload_promotion:
                    # Trigger cron for active if cron not active
                    cron_id = self.env.ref('izi_marketplace.ir_cron_promotion', False)
                    if not cron_id.active:
                        cron_id.write({'active': True})

    @mp.shopee.capture_error
    def shopee_update_promotion(self):
        for promotion in self:
            if promotion.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': promotion.mp_account_id.mp_token_id.name}
                sp_account = promotion.mp_account_id.shopee_get_account(**params)
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

            if sp_account:
                sp_discount = ShopeePromotion(sp_account)
                update_promotion_params = {
                    'promotion_id': int(promotion.mp_external_id),
                    'promotion_name': promotion.name,
                    'start_time': int(datetime.timestamp(promotion.date_start)),
                    'end_time': int(datetime.timestamp(promotion.date_end))
                }
                if promotion.code == 'discount':
                    # get Discount detail
                    discount_detail = sp_discount.get_discount(**{'discount_id': int(promotion.mp_external_id)})

                    # get current promotion item
                    current_promotion_item = {}
                    for product_disc in self.product_discount_ids:
                        mp_product_exid = product_disc.mp_product_id.mp_external_id
                        if not product_disc.mp_product_variant_id:
                            current_promotion_item[mp_product_exid] = [mp_product_exid]
                        else:
                            variant_id = product_disc.mp_product_variant_id.mp_external_id
                            if mp_product_exid not in current_promotion_item:
                                current_promotion_item[mp_product_exid] = [variant_id]
                            else:
                                current_promotion_item[mp_product_exid].append(variant_id)

                    # delete all product discount
                    for item in discount_detail['item_list']:
                        if not item['model_list']:
                            delete_discount_item = sp_discount.delete_discount_item(
                                **{'item_id': item['item_id'],
                                    'discount_id': discount_detail['discount_id']
                                   })
                        else:
                            for model in item['model_list']:
                                model_list = current_promotion_item[str(item['item_id'])]
                                delete_discount_item = sp_discount.delete_discount_item(
                                    **{'item_id': item['item_id'],
                                        'discount_id': discount_detail['discount_id'],
                                        'model_id': model['model_id']
                                       })

                    if promotion.is_uploaded:
                        if promotion.date_start < datetime.fromtimestamp(time.mktime(time.gmtime(discount_detail['start_time']))):
                            raise UserError('The new start time must later than original start time.')

                        # upload a new adding discount item
                        item_list_by_exid = promotion.shopee_generate_item_list()

                        add_discount_item_params = {
                            'discount_id': promotion.mp_external_id,
                            'item_list': [],
                        }
                        for item in item_list_by_exid:
                            add_discount_item_params['item_list'].append(item_list_by_exid[item])
                        discount_item_data = sp_discount.add_discount_item(**add_discount_item_params)
                        if discount_item_data['error_list']:
                            raise UserError(discount_item_data['error_list'][0]['fail_message'])

                        # upload discount
                        discount_data = sp_discount.update_discount(**update_promotion_params)
                        if discount_data:
                            promotion.write({
                                'mp_external_id': str(discount_data.get('discount_id')),
                            })

                elif promotion.code == 'voucher':
                    # get Discount detail
                    voucher_detail = sp_discount.get_voucher(**{'voucher_id': int(promotion.mp_external_id)})
                    if promotion.is_uploaded:
                        if promotion.date_start < datetime.fromtimestamp(time.mktime(time.gmtime(voucher_detail['start_time']))):
                            raise UserError('The new start time must later than original start time.')
                    update_promotion_params.update({
                        'voucher_code': promotion.sp_voucher_code,
                        'voucher_type': int(promotion.sp_voucher_type),
                        'reward_type': int(promotion.sp_reward_type),
                        'usage_quantity': promotion.sp_usage_quantity,
                        'min_basket_price': promotion.sp_min_basket_price,
                        'display_channel_list': promotion.sp_display_channel_list.mapped('code')
                    })
                    if promotion.sp_reward_type == '1':
                        update_promotion_params.update({
                            'discount_amount': promotion.sp_discount_amount,
                        })
                    else:
                        update_promotion_params.update({
                            'percentage': int(promotion.sp_discount_percentage),
                            'max_price': promotion.sp_max_price,
                        })

                    if promotion.sp_voucher_type == '2':
                        item_list = [int(item.mp_product_id.mp_external_id) for item in promotion.sp_voucher_item_list]
                        update_promotion_params.update({
                            'item_id_list': item_list,
                        })

                    # upload voucher
                    voucher_data = sp_discount.update_voucher(**update_promotion_params)
                    if voucher_data:
                        promotion.write({
                            'mp_external_id': str(voucher_data.get('voucher_id')),
                        })

                elif promotion.code == 'bundle':
                    # get Bundle detail
                    bundle_detail = sp_discount.get_bundle(**{'bundle_deal_id': int(promotion.mp_external_id)})
                    bundle_item = sp_discount.get_bundle_item(**{'bundle_deal_id': int(promotion.mp_external_id)})

                    if promotion.is_uploaded:
                        if promotion.date_start < datetime.fromtimestamp(time.mktime(time.gmtime(bundle_detail['start_time']))):
                            raise UserError('The new start time must later than original start time.')

                    # delete all bundle deal item
                    delete_bundle_item_req = {
                        'bundle_deal_id': int(promotion.mp_external_id),
                        'item_list': []
                    }
                    for item in bundle_item:
                        delete_bundle_item_req['item_list'].append({
                            'item_id': item['item_id']
                        })
                    if delete_bundle_item_req['item_list']:
                        delete_bundle_item_resp = sp_discount.delete_bundle_item(**delete_bundle_item_req)

                    add_bundle_item_params = {
                        'bundle_deal_id': promotion.mp_external_id,
                        'item_list': [],
                    }
                    for item in promotion.sp_bundle_item_list:
                        add_bundle_item_params['item_list'].append({
                            'item_id': int(item.mp_product_id.mp_external_id),
                            'status': 1
                        })
                    bundle_item_data = sp_discount.add_bundle_item(**add_bundle_item_params)
                    if bundle_item_data.get('error_list', False):
                        raise UserError(discount_item_data['error_list'][0]['fail_message'])

                    # upload discount
                    update_promotion_params.update({
                        'min_amount': promotion.sp_bundle_min_amount,
                        'purchase_limit': promotion.sp_bundle_purchase_limit,
                    })

                    new_date_start = promotion.date_start - timedelta(seconds=promotion.date_start.second)
                    new_date_end = promotion.date_end - timedelta(seconds=promotion.date_end.second)
                    if new_date_start == datetime.fromtimestamp(time.mktime(time.gmtime(bundle_detail['start_time']))):
                        update_promotion_params.pop('start_time')
                    if new_date_end == datetime.fromtimestamp(time.mktime(time.gmtime(bundle_detail['end_time']))):
                        update_promotion_params.pop('end_time')

                    if bundle_detail['bundle_deal_rule']['rule_type'] != int(promotion.sp_bundle_rule_type):
                        update_promotion_params.update({
                            'rule_type': int(promotion.sp_bundle_rule_type)
                        })

                    if bundle_detail['bundle_deal_rule']['discount_percentage'] != promotion.sp_bundle_discount_percentage:
                        update_promotion_params.update({
                            'discount_percentage': int(promotion.sp_bundle_discount_percentage),
                        })
                    if bundle_detail['bundle_deal_rule']['discount_value'] != promotion.sp_bundle_discount_value:
                        update_promotion_params.update({
                            'discount_value': promotion.sp_bundle_discount_value,
                        })
                    if bundle_detail['bundle_deal_rule']['fix_price'] != promotion.sp_bundle_fix_price:
                        update_promotion_params.update({
                            'fix_price': promotion.sp_bundle_fix_price,
                        })

                    bundle_data = sp_discount.update_bundle(**update_promotion_params)
                    if bundle_data:
                        promotion.write({
                            'mp_external_id': str(discount_data.get('discount_id')),
                        })

                elif promotion.code == 'addon':
                    # upload addon
                    if promotion.sp_addon_purchase_limit != 0:
                        update_promotion_params.update({
                            'promotion_purchase_limit': promotion.sp_addon_purchase_limit
                        })
                    if promotion.sp_addon_purchase_min_spend != 0:
                        update_promotion_params.update({
                            'purchase_min_spend': promotion.sp_addon_purchase_min_spend
                        })
                    if promotion.sp_addon_per_gift_num != 0:
                        update_promotion_params.update({
                            'per_gift_num': promotion.sp_addon_per_gift_num
                        })
                    addon_data = sp_discount.update_addon(**update_promotion_params)
                    if addon_data:
                        promotion.write({
                            'mp_external_id': str(addon_data.get('add_on_deal_id')),
                        })

                    # delete all main item
                    main_item = sp_discount.get_addon_main_item(addon_deal_id=int(promotion.mp_external_id))
                    delete_addon_main_item = sp_discount.delete_addon_main_item(
                        **{'main_item_list': [int(item['item_id']) for item in main_item],
                            'add_on_deal_id': int(promotion.mp_external_id),
                           })

                    # adding all main item
                    add_addon_main_item_params = {
                        'add_on_deal_id': int(promotion.mp_external_id),
                        'main_item_list': [],
                    }
                    for item in promotion.sp_addon_main_item_ids:
                        addon_main_item = {
                            'item_id': item.mp_product_id.mp_external_id,
                            'status': 1
                        }
                        add_addon_main_item_params['main_item_list'].append(addon_main_item)
                    addon_main_item_data = sp_discount.add_addon_main_item(**add_addon_main_item_params)

                    # delete all sub item
                    sub_item = sp_discount.get_addon_sub_item(addon_deal_id=int(promotion.mp_external_id))
                    if sub_item:
                        delete_addon_sub_item_params = {
                            'add_on_deal_id': int(promotion.mp_external_id),
                            'sub_item_list': []
                        }

                        for item in sub_item:
                            vals = {
                                'item_id': item['item_id']
                            }
                            if 'model_id' in item:
                                vals.update({
                                    'model_id': item['model_id']
                                })
                            delete_addon_sub_item_params['sub_item_list'].append(vals)
                        delete_addon_sub_item = sp_discount.delete_addon_sub_item(**delete_addon_sub_item_params)

                    # adding addon sub item
                    add_addon_sub_item_params = {
                        'add_on_deal_id': int(promotion.mp_external_id),
                        'sub_item_list': [],
                    }
                    for item in promotion.sp_addon_sub_item_ids:
                        addon_sub_item = {
                            'item_id': int(item.mp_product_id.mp_external_id),
                            'status': 1,
                            'sub_item_input_price': item.final_item_price,
                        }
                        if item.mp_product_variant_id:
                            addon_sub_item.update({
                                'model_id': int(item.mp_product_variant_id.mp_external_id)
                            })
                        if item.purchase_limit != 0:
                            addon_sub_item.update({
                                'sub_item_limit': int(item.purchase_limit)
                            })
                        add_addon_sub_item_params['sub_item_list'].append(addon_sub_item)
                    addon_sub_item_data = sp_discount.add_addon_sub_item(**add_addon_sub_item_params)

    @mp.shopee.capture_error
    def shopee_delete_promotion(self):
        if self.mp_account_id.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_account_id.mp_token_id.name}
            sp_account = self.mp_account_id.shopee_get_account(**params)
        else:
            raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

        if sp_account:
            if self.is_uploaded:
                sp_discount = ShopeePromotion(sp_account)
                delete_discount_params = {
                    'promotion_id': int(self.mp_external_id),
                }
                if self.code == 'discount':
                    # delete discount
                    response = sp_discount.delete_discount(**delete_discount_params)
                    if not response:
                        raise UserError('Failed to delete promotion.')
                    else:
                        self.write({
                            'active': False,
                            'state': 'draft',
                            'is_uploaded': False,
                            'mp_external_id': None
                        })
                elif self.code == 'voucher':
                    # delete voucher
                    response = sp_discount.delete_voucher(**delete_discount_params)
                    if not response:
                        raise UserError('Failed to delete promotion.')
                    else:
                        self.write({
                            'active': False,
                            'state': 'draft',
                            'is_uploaded': False,
                            'mp_external_id': None
                        })
                elif self.code == 'bundle':
                    # delete bundle
                    response = sp_discount.delete_bundle(**delete_discount_params)
                    if not response:
                        raise UserError('Failed to delete promotion.')
                    else:
                        self.write({
                            'active': False,
                            'state': 'draft',
                            'is_uploaded': False,
                            'mp_external_id': None
                        })
                elif self.code == 'addon':
                    # delete addon
                    response = sp_discount.delete_addon(**delete_discount_params)
                    if not response:
                        raise UserError('Failed to delete promotion.')
                    else:
                        self.write({
                            'active': False,
                            'state': 'draft',
                            'is_uploaded': False,
                            'mp_external_id': None
                        })
            else:
                self.write({
                    'active': False,
                    'state': 'draft',
                    'is_uploaded': False,
                    'mp_external_id': None
                })

    @mp.shopee.capture_error
    def shopee_stop_promotion(self):
        if self.mp_account_id.mp_token_id.state == 'valid':
            params = {'access_token': self.mp_account_id.mp_token_id.name}
            sp_account = self.mp_account_id.shopee_get_account(**params)
        else:
            raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')

        if sp_account:
            if self.is_uploaded and self.state == 'run':
                sp_discount = ShopeePromotion(sp_account)
                end_discount_params = {
                    'promotion_id': int(self.mp_external_id),
                }
                if self.code == 'discount':
                    # stop discount
                    response = sp_discount.end_discount(**end_discount_params)
                    if not response:
                        raise UserError('Failed to stop promotion.')
                    else:
                        self.write({
                            'state': 'stop'
                        })
                elif self.code == 'voucher':
                    response = sp_discount.end_voucher(**end_discount_params)
                    if not response:
                        raise UserError('Failed to stop promotion.')
                    else:
                        self.write({
                            'state': 'stop'
                        })
                elif self.code == 'bundle':
                    response = sp_discount.end_bundle(**end_discount_params)
                    if not response:
                        raise UserError('Failed to stop promotion.')
                    else:
                        self.write({
                            'state': 'stop'
                        })
                elif self.code == 'addon':
                    response = sp_discount.end_addon(**end_discount_params)
                    if not response:
                        raise UserError('Failed to stop promotion.')
                    else:
                        self.write({
                            'state': 'stop'
                        })
            else:
                self.write({
                    'state': 'stop'
                })

    def shopee_sync_promotion(self):
        wiz_mp_promotion_obj = self.env['wiz.mp.promotion']

        self.ensure_one()

        wiz_mp_promotion = wiz_mp_promotion_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_promotion_id',
            'mp_promotion_id': self.mp_external_id,
            'sp_promotion_type': self.promotion_type.code
        })
        return wiz_mp_promotion.get_promotion()


class MPPromotionProgramLine(models.Model):
    _inherit = 'mp.promotion.program.line'

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_exid': ('mp_promotion_exid', None),
            'purchase_limit': ('purchase_limit', None),
            'item_stock': ('item_promotion_stock', None),
            'price_mode': ('price_mode', None),
            'item_price': ('item_promotion_price', None),
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            product = mp_product_obj
            if data:
                product_id = data

                mp_product = mp_product_obj.search_mp_records('shopee', product_id)

                if mp_product.exists():
                    product = mp_product.id

            return product

        def _handle_mp_product_variant_id(env, data):
            mp_product_variant_obj = env['mp.product.variant']
            product = mp_product_variant_obj
            if data:
                model_id = data
                mp_product_variant = mp_product_variant_obj.search_mp_records('shopee', model_id)
                if mp_product_variant.exists():
                    product = mp_product_variant.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('item_id', _handle_mp_product_id),
            'mp_product_variant_id': ('model_id', _handle_mp_product_variant_id),
            'mp_product_name': ('item_name', None),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgramLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)


class SPVoucherChannel(models.Model):
    _name = 'mp.shopee.voucher.channel'
    _description = 'Shopee Vocuher Channel'

    name = fields.Char(string='Name')
    code = fields.Integer(string='code')


class SPVoucherProduct(models.Model):
    _name = 'mp.shopee.voucher.product'
    _description = 'Shopee Voucher Product'
    _inherit = ['mp.base']

    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='Promotion ID', ondelete='cascade')
    mp_account_id = fields.Many2one(comodel_name='mp.account', related='promotion_id.mp_account_id', store=True)
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    mp_product_exid = fields.Char(string='MP Product EXID')
    item_original_price = fields.Char(string='Original Price', readonly=True,
                                      compute='_get_original_price', store=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_exid': ('mp_promotion_exid', None),
            'mp_product_exid': ('mp_product_exid', None)
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            product = mp_product_obj
            if data:
                product_id = data

                mp_product = mp_product_obj.search_mp_records('shopee', product_id)

                if mp_product.exists():
                    product = mp_product.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('mp_product_id', _handle_mp_product_id)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SPVoucherProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.depends('mp_product_id', 'item_original_price')
    def _get_original_price(self):
        for rec in self:
            if not rec.mp_product_id:
                rec.item_original_price = '0'
            else:
                if rec.mp_product_id.mp_product_variant_ids:
                    list_price = sorted(rec.mp_product_id.mp_product_variant_ids.mapped('list_price'))
                    if len(list_price) > 1:
                        rec.item_original_price = '%s - %s' % (str(list_price[0]), str(list_price[-1]))
                    elif list_price:
                        rec.item_original_price = '%s' % (str(list_price[0]))
                    else:
                        rec.item_original_price = '0'
                else:
                    rec.item_original_price = str(rec.mp_product_id.list_price)


class SPBundleProduct(models.Model):
    _name = 'mp.shopee.bundle.product'
    _description = 'Shopee Bundle Product'
    _inherit = ['mp.base']

    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='Promotion', ondelete='cascade')
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    mp_account_id = fields.Many2one(comodel_name='mp.account', related='promotion_id.mp_account_id', store=True)
    mp_product_exid = fields.Char(string='MP Product EXID')
    item_original_price = fields.Char(string='Original Price', readonly=True,
                                      compute='_get_original_price', store=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_exid': ('mp_promotion_exid', None),
            'mp_product_exid': ('item_id', None),
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            product = mp_product_obj
            if data:
                product_id = data

                mp_product = mp_product_obj.search_mp_records('shopee', product_id)

                if mp_product.exists():
                    product = mp_product.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('item_id', _handle_mp_product_id)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SPBundleProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.depends('mp_product_id', 'item_original_price')
    def _get_original_price(self):
        for rec in self:
            if not rec.mp_product_id:
                rec.item_original_price = '0'
            else:
                if rec.mp_product_id.mp_product_variant_ids:
                    list_price = sorted(rec.mp_product_id.mp_product_variant_ids.mapped('list_price'))
                    if len(list_price) > 1:
                        rec.item_original_price = '%s - %s' % (str(list_price[0]), str(list_price[-1]))
                    elif list_price:
                        rec.item_original_price = '%s' % (str(list_price[0]))
                    else:
                        rec.item_original_price = '0'
                else:
                    rec.item_original_price = str(rec.mp_product_id.list_price)


class SPAddonMainProduct(models.Model):
    _name = 'mp.shopee.addon.main.product'
    _description = 'Shopee Addon Main Product'
    _inherit = ['mp.base']

    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='Promotion', ondelete='cascade')
    mp_account_id = fields.Many2one(comodel_name='mp.account', related='promotion_id.mp_account_id', store=True)
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    mp_product_exid = fields.Char(string='MP Product EXID')
    item_original_price = fields.Char(string='Original Price', readonly=True,
                                      compute='_get_original_price', store=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_exid': ('mp_promotion_exid', None),
            'mp_product_exid': ('item_id', None),
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            product = mp_product_obj
            if data:
                product_id = data

                mp_product = mp_product_obj.search_mp_records('shopee', product_id)

                if mp_product.exists():
                    product = mp_product.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('item_id', _handle_mp_product_id)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SPAddonMainProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.depends('mp_product_id', 'item_original_price')
    def _get_original_price(self):
        for rec in self:
            if not rec.mp_product_id:
                rec.item_original_price = '0'
            else:
                if rec.mp_product_id.mp_product_variant_ids:
                    list_price = sorted(rec.mp_product_id.mp_product_variant_ids.mapped('list_price'))
                    if len(list_price) > 1:
                        rec.item_original_price = '%s - %s' % (str(list_price[0]), str(list_price[-1]))
                    elif list_price:
                        rec.item_original_price = '%s' % (str(list_price[0]))
                    else:
                        rec.item_original_price = '0'
                else:
                    rec.item_original_price = str(rec.mp_product_id.list_price)


class SPAddonSubProduct(models.Model):
    _name = 'mp.shopee.addon.sub.product'
    _description = 'Shopee Addon Sub Product'
    _inherit = ['mp.base']

    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='Promotion', ondelete='cascade')
    mp_account_id = fields.Many2one(comodel_name='mp.account', related='promotion_id.mp_account_id', store=True)
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    mp_product_variant_count = fields.Integer(related='mp_product_id.mp_product_variant_count')
    mp_product_variant_id = fields.Many2one(comodel_name='mp.product.variant',
                                            string='MP Product Variant')
    item_original_price = fields.Float(string='Original Price', readonly=True,
                                       compute='_get_original_price', store=True,)
    purchase_limit = fields.Integer(string='Purchase Limit', default=1)
    price_mode = fields.Selection([("percentage", "Percentage Price"),
                                  ("fixed", "Fixed Price")], string='Price Mode', default='percentage')
    item_price = fields.Float(string='Discount Price')
    final_item_price = fields.Float(string='Final Price', compute='_get_price_final', store=True,)
    mp_product_exid = fields.Char(string='MP Product EXID')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_exid': ('mp_promotion_exid', None),
            'purchase_limit': ('sub_item_limit', None),
            'price_mode': ('price_mode', None),
            'item_price': ('price/promo_input_price', None),
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            product = mp_product_obj
            if data['item_id']:
                product_id = data['item_id']

                mp_product = mp_product_obj.search_mp_records('shopee', product_id)

                if mp_product.exists():
                    product = mp_product.id

            return product

        def _handle_mp_product_variant_id(env, data):
            mp_product_variant_obj = env['mp.product.variant']
            product = mp_product_variant_obj
            if 'model_id' in data:
                if data['model_id']:
                    model_id = data
                    mp_product_variant = mp_product_variant_obj.search_mp_records('shopee', model_id)
                    if mp_product_variant.exists():
                        product = mp_product_variant.id

            return product

        def _handle_mp_product_exid(env, data):
            if 'model_id' in data:
                return data['model_id']
            else:
                return data['item_id']

        mp_field_mapping.update({
            'mp_product_id': ('item_info', _handle_mp_product_id),
            'mp_product_variant_id': ('item_info', _handle_mp_product_variant_id),
            'mp_product_exid': ('item_info', _handle_mp_product_exid),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SPAddonSubProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.depends('mp_product_id', 'item_original_price', 'mp_product_variant_id')
    def _get_original_price(self):
        for rec in self:
            if not rec.mp_product_id:
                rec.item_original_price = 0
            else:
                if rec.mp_product_variant_id:
                    rec.item_original_price = rec.mp_product_variant_id.list_price
                else:
                    rec.item_original_price = rec.mp_product_id.list_price

    @api.depends('item_original_price', 'price_mode', 'item_price', 'final_item_price')
    def _get_price_final(self):
        for rec in self:
            if rec.item_original_price == 0:
                rec.final_item_price = 0
            else:
                if rec.price_mode == 'percentage':
                    rec.final_item_price = rec.item_original_price - (rec.item_original_price*rec.item_price/100)
                elif rec.price_mode == 'fixed':
                    rec.final_item_price = rec.item_price
