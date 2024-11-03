# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
import time
import json
import pytz
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.izi_marketplace.objects.utils.tools import mp, generate_id


class MPPromotionProgram(models.Model):
    _inherit = 'mp.promotion.program'

    # _TTS_PROMOTION_STATUS = [
    #     ('2', 'ONGOING'),
    #     ('3', 'EXPIRED'),
    #     ('1', 'UPCOMING'),
    #     ('4', 'DEACTIVATED')
    # ]
    _TTS_PROMOTION_STATUS = [
        ('ONGOING', 'ONGOING'),
        ('EXPIRED', 'EXPIRED'),
        ('NOT_START', 'NOT START'),
        ('DEACTIVATED', 'DEACTIVATED')
    ]

    _PRODUCT_TYPE = [
        ("1", "SPU"),
        ("2", "SKU")
    ]

    _PROMOTION_TYPE = [
        ("1", "FixedPrice"),
        ("2", "DirectDiscount"),
        ("3", "FlashSale")
    ]

    tts_promotion_id = fields.Char(string='TTS Promotion ID', index=True)
    tts_promotion_status = fields.Selection(selection=_TTS_PROMOTION_STATUS, string='Tiktok Promotion Status')
    tts_promotion_type = fields.Selection(selection=_PROMOTION_TYPE, string='TTS Promotion Type')
    tts_product_type = fields.Selection(selection=_PRODUCT_TYPE, string='Bundle Type')

    # tts_bundle_purchase_limit = fields.Integer(string='Max Order', default=0,
    #                                           help='Maximum bundle package in one order')
    # tts_bundle_quota = fields.Integer(string='Quota', default=0,
    #                                  help='Original quota for bundle')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'tts_promotion_id': ('promotion_id', None),
            'mp_external_id': ('promotion_id', None),
            'name': ('name', lambda env, r: str(r) if r else None),
            'tts_promotion_status': ('status', lambda env, r: str(r) if r else None),
            'tts_promotion_type': ('promotion_type', lambda env, r: str(r) if r else None),
            'tts_product_type': ('product_type', lambda env, r: str(r) if r else None),
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
                    ('marketplace', '=', 'tiktok'),
                    ('code', '=', data)
                ]
                mp_promotion_type = env['mp.promotion.program.type'].search(domain, limit=1)
                if mp_promotion_type:
                    return mp_promotion_type.id
                else:
                    return None
            return None

        mp_field_mapping.update({
            'date_start': ('start_time', _convert_iso_to_datetime),
            'date_end': ('end_time', _convert_iso_to_datetime),
            'state': ('status', _handle_promotion_state),
            'promotion_type': ('promotion_type', _handle_promotion_type),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgram, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        records = super(MPPromotionProgram, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tiktok':
            records = self.tiktok_process_promotion_lines(mp_account, records)
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(MPPromotionProgram, self)._finish_update_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tiktok':
            records = self.tiktok_process_promotion_lines(mp_account, records)
        return records

    def tiktok_process_promotion_lines(self, mp_account, records):
        mp_account_ctx = mp_account.generate_context()
        _logger = self.env['mp.base']._logger

        for record in records:
            tts_promotion_line_raws, tts_promotion_line_sanitizeds = [], []
            tts_order_raw = json.loads(record.raw, strict=False)
            now = datetime.now()
            if record.date_start < now and record.date_end > now:
                record.write({
                    'tts_promotion_status': '2',
                    'state': 'run'
                })
            elif record.date_start > now and record.date_end > now:
                record.write({
                    'tts_promotion_status': '1',
                    'state': 'wait'
                })
            else:
                record.write({
                    'tts_promotion_status': '3',
                    'state': 'stop'
                })

            if record.promotion_type.code == 'discount':
                mp_promotion_program_line_obj = self.env['mp.promotion.program.line']
                item_list = tts_order_raw['slash_price_line']
                tts_discount_line = [
                    # Insert promotion into item_list
                    dict(tts_discount_line_raw,
                         **dict([('promotion_id', record.id)]),
                         **dict([('price_mode', 'fixed')]),
                         **dict([('mp_promotion_exid', record.mp_external_id)]))
                    for tts_discount_line_raw in item_list
                ]
                tts_data_raw, tts_data_sanitized = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=tts_discount_line)
                tts_promotion_line_raws.extend(tts_data_raw)
                tts_promotion_line_sanitizeds.extend(tts_data_sanitized)

                check_existing_records_params = {
                    'identifier_field': 'tts_slash_price_id',
                    'raw_data': tts_promotion_line_raws,
                    'mp_data': tts_promotion_line_sanitizeds,
                    'multi': isinstance(tts_promotion_line_sanitizeds, list)
                }
                check_existing_records = mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).check_existing_records(**check_existing_records_params)
                mp_promotion_program_line_obj.with_context(
                    mp_account_ctx).handle_result_check_existing_records(check_existing_records)

    # @mp.tiktok.capture_error
    # def tiktok_upload_promotion(self):
    #     upload_promotion = False
    #
    #     def to_api_timestamp(dt, dt_tz='UTC'):
    #         dts_utc = pytz.timezone('UTC').localize(dt).astimezone(pytz.UTC)
    #
    #         # +7 Hours For Parameter UNIX Timestamp in API tiktok. TO CONVERT THIS CAN NOT USE TIMEZONE and .timestamp(), because .timestamp() always in UTC+0
    #         dt_tiktok = dts_utc + timedelta(hours=7)
    #
    #         return int(dt_tiktok.timestamp())
    #
    #         # dt_tz = pytz.timezone(dt_tz)
    #         # api_dt = dt_tz.localize(dt).astimezone(pytz.timezone('Asia/Jakarta'))
    #         # return int(api_dt.replace(tzinfo=pytz.utc).timestamp())
    #
    #     for promotion in self:
    #         tts_account = promotion.mp_account_id.tiktok_get_account()
    #         tts_campaign = tiktokCampaign(tts_account, api_version="v1")
    #         datetime_now = datetime.now() + timedelta(minutes=10)
    #         if promotion.date_start < datetime_now:
    #             raise UserError('Promotion start date is set at least 10 minutes from time now.')
    #
    #         if promotion.code == 'discount':
    #             payload = []
    #             for item in promotion.product_discount_ids:
    #                 add_promotion_params = {
    #                     'promotion_name': promotion.name,
    #                     'start_time_unix': to_api_timestamp(promotion.date_start),
    #                     'end_time_unix': to_api_timestamp(promotion.date_end),
    #                     'max_order': item.purchase_limit,
    #                 }
    #                 if item.mp_product_variant_id:
    #                     add_promotion_params.update({
    #                         'product_id': int(item.mp_product_variant_id.mp_external_id)
    #                     })
    #                 else:
    #                     add_promotion_params.update({
    #                         'product_id': int(item.mp_product_id.mp_external_id)
    #                     })
    #
    #                 if item.price_mode == 'fixed':
    #                     add_promotion_params.update({
    #                         'discounted_price': item.final_item_price
    #                     })
    #                 elif item.price_mode == 'percentage':
    #                     add_promotion_params.update({
    #                         'discount_percentage': int(item.item_price)
    #                     })
    #                 payload.append(add_promotion_params)
    #
    #             slash_price_data = tts_campaign.add_slash_price(
    #                 shop_id=promotion.mp_account_id.tts_shop_id.shop_id, data=payload)
    #             if slash_price_data.get('failed_rows_data', False):
    #                 message = '\n'.join(e for e in slash_price_data.get('failed_rows_data'))
    #                 raise UserError(message)
    #             else:
    #                 obj_start_date = self.env['mp.base'].datetime_convert_tz(
    #                     promotion.date_start, 'UTC', 'Asia/Jakarta')
    #                 str_start_date = fields.Datetime.to_string(obj_start_date)
    #
    #                 obj_end_date = self.env['mp.base'].datetime_convert_tz(promotion.date_end, 'UTC', 'Asia/Jakarta')
    #                 str_end_date = fields.Datetime.to_string(obj_end_date)
    #
    #                 promotion_name = 'Tiktok Slash Price %s - %s' % (str_start_date, str_end_date)
    #                 promotion_id = generate_id(promotion_name)
    #                 promotion.write({
    #                     'mp_external_id': str(promotion_id),
    #                     'is_uploaded': True,
    #                     'state': 'wait'
    #                 })
    #
    #         elif promotion.code == 'bundle':
    #             pass
    #
    # def tiktok_update_promotion(self):
    #     pass
    #
    # def tiktok_delete_promotion(self):
    #     pass
    #
    # def tiktok_stop_promotion(self):
    #     pass
    #
    # def tiktok_sync_promotion(self):
    #     wiz_mp_promotion_obj = self.env['wiz.mp.promotion']
    #
    #     self.ensure_one()
    #
    #     wiz_mp_promotion = wiz_mp_promotion_obj.create({
    #         'mp_account_id': self.mp_account_id.id,
    #         'params': 'by_mp_promotion_id',
    #         'mp_promotion_id': self.mp_external_id,
    #         'tts_promotion_type': self.promotion_type.code
    #     })
    #     return wiz_mp_promotion.get_promotion()


class MPPromotionProgramLine(models.Model):
    _inherit = 'mp.promotion.program.line'

    tts_slash_price_id = fields.Char(string='TTS Slash Price Product ID', index=True)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'promotion_id': ('promotion_id', None),
            'mp_external_id': ('slash_price_product_id', lambda env, r: str(r) if r else None),
            'tts_slash_price_id': ('slash_price_product_id', lambda env, r: str(r) if r else None),
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

                mp_product = mp_product_obj.search_mp_records('tiktok', product_id)

                if mp_product.exists():
                    product = mp_product.id
                else:
                    mp_product_variant = mp_product_variant_obj.search_mp_records('tiktok', product_id)
                    if mp_product_variant.exists():
                        product = mp_product_variant.mp_product_id.id

            return product

        def _handle_mp_product_variant_id(env, data):
            mp_product_variant_obj = env['mp.product.variant']
            product = mp_product_variant_obj
            if data:
                model_id = data
                mp_product_variant = mp_product_variant_obj.search_mp_records('tiktok', model_id)
                if mp_product_variant.exists():
                    product = mp_product_variant.id

            return product

        mp_field_mapping.update({
            'mp_product_id': ('product_id', _handle_mp_product_id),
            'mp_product_variant_id': ('product_id', _handle_mp_product_variant_id),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPPromotionProgramLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)

