# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
import time
import json
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import mp, generate_id
from odoo.addons.izi_tokopedia.objects.utils.tokopedia.campaign import TokopediaCampaign


class MPPromotionProgram(models.Model):
    _inherit = 'mp.promotion.program'

    _TP_PROMOTION_STATUS = [
        ('2', 'ACTIVE'),
        ('3', 'INACTIVE'),
        ('1', 'COMING SOON'),
        ('6', 'REDIRECTED')
    ]

    _BUNDLE_TYPE = [
        ("1", "PAKET DISKON"),
        ("2", "BUNDLING"),
    ]

    tp_promotion_id = fields.Char(string='TP Promotion ID', index=True)
    tp_promotion_status = fields.Selection(selection=_TP_PROMOTION_STATUS, string='Tokopedia Promotion Status')

    # Bundle Field
    tp_bundle_type = fields.Selection(selection=_BUNDLE_TYPE, string='Bundle Type')
    tp_bundle_purchase_limit = fields.Integer(string='Max Order', default=0,
                                              help='Maximum bundle package in one order')
    tp_bundle_quota = fields.Integer(string='Quota', default=0,
                                     help='Original quota for bundle')
    tp_bundle_item_list = fields.One2many(
        comodel_name='mp.tokopedia.bundle.product', inverse_name='promotion_id', string='Bundle Product List')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'tp_promotion_id': ('promotion_id', None),
            'mp_external_id': ('promotion_id', None),
            'name': ('name', lambda env, r: str(r) if r else None),
            'is_uploaded': ('is_uploaded', None),
        }

        def _convert_iso_to_datetime(env, data):
            if data:
                if '+' in data:
                    iso_str = data[:-1].split('+')[0]
                else:
                    iso_str = data[:-1].split('.')[0]
                dt = env['mp.base'].datetime_convert_tz(datetime.fromisoformat(
                    iso_str), 'Asia/Jakarta', 'UTC')
                return fields.Datetime.to_string(dt)
            else:
                return None

        def _handle_promotion_state(env, data):
            if data:
                if data == 1:
                    return 'wait'
                elif data == 2:
                    return 'run'
                elif data == 3:
                    return 'stop'
            return None

        def _handle_promotion_type(env, data):
            if data:
                domain = [
                    ('marketplace', '=', 'tokopedia'),
                    ('code', '=', data)
                ]
                mp_promotion_type = env['mp.promotion.program.type'].search(domain, limit=1)
                if mp_promotion_type:
                    return mp_promotion_type.id
                else:
                    return None
            return None

        mp_field_mapping.update({
            'date_start': ('start_date', _convert_iso_to_datetime),
            'date_end': ('end_date', _convert_iso_to_datetime),
            'state': ('slash_price_status_id', _handle_promotion_state),
            'promotion_type': ('promotion_type', _handle_promotion_type),
            'tp_promotion_status': ('slash_price_status_id', lambda env, r: str(r) if r else None),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgram, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        records = super(MPPromotionProgram, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tokopedia':
            records = self.tokopedia_process_promotion_lines(mp_account, records)
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(MPPromotionProgram, self)._finish_update_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tokopedia':
            records = self.tokopedia_process_promotion_lines(mp_account, records)
        return records

    def tokopedia_process_promotion_lines(self, mp_account, records):
        mp_account_ctx = mp_account.generate_context()
        _logger = self.env['mp.base']._logger

        for record in records:
            tp_promotion_line_raws, tp_promotion_line_sanitizeds = [], []
            tp_order_raw = json.loads(record.raw, strict=False)
            now = datetime.now()
            if record.date_start < now and record.date_end > now:
                record.write({
                    'tp_promotion_status': '2',
                    'state': 'run'
                })
            elif record.date_start > now and record.date_end > now:
                record.write({
                    'tp_promotion_status': '1',
                    'state': 'wait'
                })
            else:
                record.write({
                    'tp_promotion_status': '3',
                    'state': 'stop'
                })

            if record.promotion_type.code == 'discount':
                mp_promotion_program_line_obj = self.env['mp.promotion.program.line']
                item_list = tp_order_raw['slash_price_line']
                tp_discount_line = [
                    # Insert promotion into item_list
                    dict(tp_discount_line_raw,
                         **dict([('promotion_id', record.id)]),
                         **dict([('price_mode', 'fixed')]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for tp_discount_line_raw in item_list
                ]
                tp_data_raw, tp_data_sanitized = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=tp_discount_line)
                tp_promotion_line_raws.extend(tp_data_raw)
                tp_promotion_line_sanitizeds.extend(tp_data_sanitized)

                check_existing_records_params = {
                    'identifier_field': 'tp_slash_price_id',
                    'raw_data': tp_promotion_line_raws,
                    'mp_data': tp_promotion_line_sanitizeds,
                    'multi': isinstance(tp_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    @mp.tokopedia.capture_error
    def tokopedia_upload_promotion(self):
        upload_promotion = False

        def to_api_timestamp(dt, dt_tz='UTC'):
            dts_utc = pytz.timezone('UTC').localize(dt).astimezone(pytz.UTC)

            # +7 Hours For Parameter UNIX Timestamp in API Tokopedia. TO CONVERT THIS CAN NOT USE TIMEZONE and .timestamp(), because .timestamp() always in UTC+0
            dt_tokopedia = dts_utc + timedelta(hours=7)

            return int(dt_tokopedia.timestamp())

            # dt_tz = pytz.timezone(dt_tz)
            # api_dt = dt_tz.localize(dt).astimezone(pytz.timezone('Asia/Jakarta'))
            # return int(api_dt.replace(tzinfo=pytz.utc).timestamp())

        for promotion in self:
            tp_account = promotion.mp_account_id.tokopedia_get_account()
            tp_campaign = TokopediaCampaign(tp_account, api_version="v1")
            datetime_now = datetime.now() + timedelta(minutes=10)
            if promotion.date_start < datetime_now:
                raise UserError('Promotion start date is set at least 10 minutes from time now.')

            if promotion.code == 'discount':
                payload = []
                for item in promotion.product_discount_ids:
                    add_promotion_params = {
                        'promotion_name': promotion.name,
                        'start_time_unix': to_api_timestamp(promotion.date_start),
                        'end_time_unix': to_api_timestamp(promotion.date_end),
                        'max_order': item.purchase_limit,
                    }
                    if item.mp_product_variant_id:
                        add_promotion_params.update({
                            'product_id': int(item.mp_product_variant_id.mp_external_id)
                        })
                    else:
                        add_promotion_params.update({
                            'product_id': int(item.mp_product_id.mp_external_id)
                        })

                    if item.price_mode == 'fixed':
                        add_promotion_params.update({
                            'discounted_price': item.final_item_price
                        })
                    elif item.price_mode == 'percentage':
                        add_promotion_params.update({
                            'discount_percentage': int(item.item_price)
                        })
                    payload.append(add_promotion_params)

                slash_price_data = tp_campaign.add_slash_price(
                    shop_id=promotion.mp_account_id.tp_shop_id.shop_id, data=payload)
                if slash_price_data.get('failed_rows_data', False):
                    message = '\n'.join(e for e in slash_price_data.get('failed_rows_data'))
                    raise UserError(message)
                else:
                    obj_start_date = self.env['mp.base'].datetime_convert_tz(
                        promotion.date_start, 'UTC', 'Asia/Jakarta')
                    str_start_date = fields.Datetime.to_string(obj_start_date)

                    obj_end_date = self.env['mp.base'].datetime_convert_tz(promotion.date_end, 'UTC', 'Asia/Jakarta')
                    str_end_date = fields.Datetime.to_string(obj_end_date)

                    promotion_name = 'Tokopedia Slash Price %s - %s' % (str_start_date, str_end_date)
                    promotion_id = generate_id(promotion_name)
                    promotion.write({
                        'mp_external_id': str(promotion_id),
                        'is_uploaded': True,
                        'state': 'wait'
                    })

            elif promotion.code == 'bundle':
                pass

    def tokopedia_update_promotion(self):
        pass

    def tokopedia_delete_promotion(self):
        pass

    def tokopedia_stop_promotion(self):
        pass

    def tokopedia_sync_promotion(self):
        wiz_mp_promotion_obj = self.env['wiz.mp.promotion']

        self.ensure_one()

        wiz_mp_promotion = wiz_mp_promotion_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_promotion_id',
            'mp_promotion_id': self.mp_external_id,
            'tp_promotion_type': self.promotion_type.code
        })
        return wiz_mp_promotion.get_promotion()


class MPPromotionProgramLine(models.Model):
    _inherit = 'mp.promotion.program.line'

    tp_slash_price_id = fields.Char(string='TP Slash Price Product ID', index=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_external_id': ('slash_price_product_id', lambda env, r: str(r) if r else None),
            'tp_slash_price_id': ('slash_price_product_id', lambda env, r: str(r) if r else None),
            'mp_exid': ('slash_price_product_id', lambda env, r: str(r) if r else None),
            'purchase_limit': ('max_order', None),
            'item_stock': ('stock', None),
            'price_mode': ('price_mode', None),
            'item_price': ('discounted_price', None),
            'mp_product_name': ('name', None),
        }

        def _handle_mp_product_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']
            product = mp_product_obj
            if data:
                product_id = data

                mp_product = mp_product_obj.search_mp_records('tokopedia', product_id)

                if mp_product.exists():
                    product = mp_product.id
                else:
                    mp_product_variant = mp_product_variant_obj.search_mp_records('tokopedia', product_id)
                    if mp_product_variant.exists():
                        product = mp_product_variant.mp_product_id.id

            return product

        def _handle_mp_product_variant_id(env, data):
            mp_product_variant_obj = env['mp.product.variant']
            product = mp_product_variant_obj
            if data:
                model_id = data
                mp_product_variant = mp_product_variant_obj.search_mp_records('tokopedia', model_id)
                if mp_product_variant.exists():
                    product = mp_product_variant.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('product_id', _handle_mp_product_id),
            'mp_product_variant_id': ('product_id', _handle_mp_product_variant_id),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgramLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)


class TPBundleProduct(models.Model):
    _name = 'mp.tokopedia.bundle.product'
    _description = 'Tokopedia Bundle Product'

    _PRODUCT_STATUS = [
        ("1", "SHOWN"),
        ("2", "UNSHOWN"),
    ]

    mp_account_id = fields.Many2one(related='promotion_id.mp_account_id', string='MP Account', store=True)
    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='MP Promotion')
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    item_original_price = fields.Char(string='Original Price', readonly=True,
                                      compute='_get_original_price', store=True)
    item_bundle_price = fields.Float(string='Bundle Price')
    tp_product_status = fields.Selection(
        selection=_PRODUCT_STATUS, string='TP Product Status', compute='_set_product_status', store=True)
    show_product = fields.Boolean(string='Show Product', default=True)
    min_order = fields.Integer(string='Minimal Order', default=0)

    @api.depends('show_product', 'tp_product_status')
    def _set_product_status(self):
        for rec in self:
            if rec.show_product:
                rec.tp_product_status = "1"
            else:
                rec.tp_product_status = "2"

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
