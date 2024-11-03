# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah

from datetime import datetime, timezone
import time
import json
import requests
import base64

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    TTS_ORDER_STATUSES = [
        ('100', 'Unpaid'),
        ('105', 'On Hold'),
        ('111', 'Awaiting Shipment'),
        ('112', 'Awaiting Collection'),
        ('114', 'Partially Shipping'),
        ('121', 'In Transit'),
        ('122', 'Delivered'),
        ('130', 'Completed'),
        ('140', 'Cancelled'),
        ('201', 'Cancel Pending'),
        ('202', 'Cancel Reject'),
        ('203', 'Cancel Completed'),
    ]

    TTS_PAYMENT_METHOD = [
        ('1', 'Bank Transfer'),
        ('2', 'Cash'),
        ('3', 'Dana Wallet'),
        ('4', 'Bank Card'),
        ('5', 'OVO'),
        ('6', 'Cash On Delivery'),
        ('7', 'Gopay'),
        ('8', 'Paypal'),
        ('9', 'Apple Pay'),
        ('10', 'Klarna'),
        ('11', 'Klarna Pay Now'),
        ('12', 'Klarna Pay Later'),
        ('13', 'Klarna Pay Overtime'),
        ('14', 'True Money'),
        ('15', 'Rabbit Line Pay'),
        ('16', 'IBanking'),
        ('17', 'Touch Go'),
        ('18', 'Boost'),
        ('19', 'Zalo Pay'),
        ('20', 'Momo'),
        ('21', 'BLIK')
    ]

    tts_order_status = fields.Selection(string="Tiktok Order Status", selection=TTS_ORDER_STATUSES, required=False)
    tts_order_id = fields.Char(string="Tiktok Order ID", readonly=True)
    tts_payment_method = fields.Char(string="Tiktok Payment Method", readonly=True)
    tts_package_id = fields.Char(string='Tiktok Package ID', readonly=True)
    tts_delivery_option = fields.Char(string='Tiktok Delivery Option', readonly=True)

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, tts_order_status_field = 'tiktok', 'tts_order_status'
        tts_order_statuses = {
            'waiting': ['100'],
            'to_cancel': ['201'],
            'cancel': ['140', '203'],
            'to_process': [],
            'in_process': ['111'],
            'to_ship': ['112'],
            'in_ship': ['121'],
            'delivered': ['122'],
            'done': ['130'],
            'return': []
        }
        mp_order_statuses.append((marketplace, (tts_order_status_field, tts_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.TTS_ORDER_STATUSES)))
        super(SaleOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    @api.depends('tts_order_status')
    def _compute_mp_order_status(self):
        super(SaleOrder, self)._compute_mp_order_status()

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'mp_invoice_number': ('order_id', lambda env, r: str(r)),
            'mp_external_id': ('order_id', lambda env, r: str(r)),
            'tts_order_id': ('order_id', lambda env, r: str(r)),
            'tts_order_status': ('order_status', lambda env, r: str(r)),
            'tts_payment_method': ('payment_method', lambda env, r: str(r) if r else None),
            'mp_delivery_carrier_name': ('shipping_provider', None),
            'mp_order_notes': ('buyer_message', None),
            'mp_cancel_reason': ('cancel_reason', None),
            'mp_recipient_address_city': ('recipient_address/city', None),
            'mp_recipient_address_name': ('recipient_address/name', None),
            'mp_recipient_address_district': ('recipient_address/district', None),
            'mp_recipient_address_country': ('recipient_address/region', None),
            'mp_recipient_address_zipcode': ('recipient_address/zipcode', None),
            'mp_recipient_address_phone': ('recipient_address/phone', None),
            'mp_recipient_address_state': ('recipient_address/state', None),
            'mp_recipient_address_full': ('recipient_address/full_address', None),
            'mp_amount_total': ('payment_info/total_amount', lambda env, r: float(r) if r else None),
            'tts_delivery_option': ('delivery_option', None),
            'mp_awb_number': ('tracking_number', lambda env, r: str(r) if r else None),
            'branch_id': ('branch_id', lambda env, r: r if r else False)
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                if type(data) == str:
                    if data.find('\n'):
                        str_data = data.split('\n')[0]
                        data = int(str_data)
                    data = int(data)
                return datetime.fromtimestamp(time.mktime(time.gmtime(data/1000.0))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _get_package_id(env, data):
            if data:
                return data[0].get('package_id', None)
            else:
                return None

        def _get_tracking_number(env, data):
            if data:
                return data['tracking_number']
            else:
                return None

        mp_field_mapping.update({
            'mp_payment_date': ('paid_time', _convert_timestamp_to_datetime),
            'mp_order_date': ('create_time', _convert_timestamp_to_datetime),
            'create_date': ('create_time', _convert_timestamp_to_datetime),
            'date_order': ('create_time', _convert_timestamp_to_datetime),
            'tts_package_id': ('package_list', _get_package_id),
            'mp_pickup_done_time': ('tts_sla', _convert_timestamp_to_datetime),
            'mp_shipping_deadline': ('rts_sla', _convert_timestamp_to_datetime),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    def generate_order_line_detail_fees(self):
        self.ensure_one()
        mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        vals = {
            'product_id': mp_delivery_product_tmpl.product_variant_id.id
        }

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()

        order_line_obj = self.env['sale.order.line'].with_context(mp_account_ctx)

        tts_order_detail_raws, tts_order_detail_sanitizeds = [], []

        if mp_account.marketplace == 'tiktok':
            for record in records:
                tts_order_raw = json.loads(record.raw, strict=False)
                list_item_field = ['product_id', 'sku_id', 'product_name', 'sku_name',
                                   'sku_original_price', 'sku_sale_price']

                item_list = tts_order_raw['item_list']
                for item in item_list:
                    item['item_info'] = dict([(key, item[key]) for key in list_item_field])

                tts_order_details = [
                    # Insert order_id into tp_order_detail_raw
                    dict(tts_order_detail_raw,
                         **dict([('order_id', record.id)]),
                         **dict([('mp_order_exid', record.mp_invoice_number)]))
                    for tts_order_detail_raw in json_digger(tts_order_raw, 'item_list')
                ]
                tts_data_raw, tts_data_sanitized = order_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=tts_order_details)
                tts_order_detail_raws.extend(tts_data_raw)
                tts_order_detail_sanitizeds.extend(tts_data_sanitized)
                # record.generate_order_line_detail_fees(tts_order_detail_raws, tts_order_detail)

            def identify_order_line(record_obj, values):
                return record_obj.search([('order_id', '=', values['order_id']),
                                          ('product_id', '=', values['product_id'])], limit=1)

            check_existing_records_params = {
                'identifier_method': identify_order_line,
                'raw_data': tts_order_detail_raws,
                'mp_data': tts_order_detail_sanitizeds,
                'multi': isinstance(tts_order_detail_sanitizeds, list)
            }
            check_existing_records = order_line_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            order_line_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)
            if self._context.get('skip_error'):
                record_ids_to_unlink = []
                for record in records:
                    tts_order_raw = json.loads(record.raw, strict=False)
                    item_list = tts_order_raw.get('item_list', [])
                    record_line = record.order_line.mapped('product_type')
                    if not record_line:
                        record_ids_to_unlink.append(record.id)
                    elif 'product' not in record_line:
                        record_ids_to_unlink.append(record.id)
                    elif len(item_list) != record_line.count('product'):
                        record_ids_to_unlink.append(record.id)

                records.filtered(lambda r: r.id in record_ids_to_unlink).unlink()

        records = super(SaleOrder, self)._finish_create_records(records)
        return records

    def tiktok_generate_delivery_line(self):
        tiktok_logistic_obj = self.env['mp.tiktok.logistic']
        tiktok_logistic_provider_obj = self.env['mp.tiktok.logistic.provider']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            tts_order_raw = json.loads(order.raw, strict=False)
            tts_order_shipping_id = json_digger(tts_order_raw, 'shipping_provider_id')
            tts_order_shipping_name = json_digger(tts_order_raw, 'shipping_provider')
            shipping_fee = tts_order_raw.get('payment_info').get('original_shipping_fee')
            if not delivery_line:
                domain = [('mp_account_id', '=', self.mp_account_id.id)]
                if tts_order_shipping_id:
                    domain.append(('mp_external_id', '=', tts_order_shipping_id))
                tts_logistic_rec = tiktok_logistic_provider_obj.search(domain, limit=1)
                delivery_product = tts_logistic_rec.get_delivery_product()
                if not delivery_product:
                    raise ValidationError('Please define delivery product on "%s"' % tts_order_shipping_name)

                # shipping_fee = sp_order_raw.get('actual_shipping_fee', 0)
                # if shipping_fee == 0:
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': delivery_product.id,
                        'name': tts_order_shipping_name or 'Shipping',
                        'product_uom_qty': 1,
                        'tax_id': False,
                        'price_unit': shipping_fee,
                        'is_delivery': True
                    })]
                })
            else:
                if delivery_line.name != tts_order_shipping_name:
                    delivery_line.update({
                        'name': tts_order_shipping_name,
                    })
            order._reset_sequence()

    # @api.multi
    # def tiktok_generate_adjusment_line(self):
    #     for order in self:
    #         adjustment_line = order.order_line.filtered(lambda l: l.is_adjustment)
    #         if not adjustment_line:
    #             sp_order_raw = json.loads(order.raw, strict=False)
    #             total_adjustment = json_digger(sp_order_raw, 'order_income/buyer_transaction_fee',
    #                                            default=0)
    #             if total_adjustment > 0:
    #                 adjustment_product = order.mp_account_id.adjustment_product_id
    #                 if not adjustment_product:
    #                     raise ValidationError(
    #                         'Please define global discount product on'
    #                         ' this marketplace account: "%s"' % order.mp_account_id.name)
    #                 order.write({
    #                     'order_line': [(0, 0, {
    #                         'sequence': 999,
    #                         'product_id': adjustment_product.id,
    #                         'product_uom_qty': 1,
    #                         'price_unit': total_adjustment,
    #                         'is_adjustment': True
    #                     })]
    #                 })

    #         tiktok_coins_line = order.order_line.filtered(lambda l: l.is_tiktok_coins)
    #         if not tiktok_coins_line:
    #             sp_order_raw = json.loads(order.raw, strict=False)
    #             total_coins = json_digger(sp_order_raw, 'order_income/coins',
    #                                       default=0)
    #             if total_coins > 0:
    #                 tiktok_coins_product = order.mp_account_id.sp_coins_product_id
    #                 if not tiktok_coins_product:
    #                     raise ValidationError(
    #                         'Please define global discount product on'
    #                         ' this marketplace account: "%s"' % order.mp_account_id.name)
    #                 order.write({
    #                     'order_line': [(0, 0, {
    #                         'sequence': 999,
    #                         'name': 'Tiktok Coins',
    #                         'product_id': tiktok_coins_product.id,
    #                         'product_uom_qty': 1,
    #                         'price_unit': total_coins,
    #                         'is_tiktok_coins': True
    #                     })]
    #                 })

    # @api.multi
    def tiktok_generate_global_discount_line(self):
        for order in self:
            seller_discount_line = order.order_line.filtered(lambda l: l.is_tts_seller_discount)
            platform_discount_line = order.order_line.filtered(lambda l: l.is_tts_platform_discount)
            shipping_seller_discount_line = order.order_line.filtered(lambda l: l.is_tts_shipping_seller_discount)
            shipping_platform_discount_line = order.order_line.filtered(lambda l: l.is_tts_shipping_platform_discount)

            tts_order_raw = json.loads(order.raw, strict=False)
            seller_discount = json_digger(tts_order_raw, 'payment_info/seller_discount', default=0)
            platform_discount = json_digger(tts_order_raw, 'payment_info/platform_discount', default=0)
            shipping_fee_seller_discount = json_digger(tts_order_raw, 'payment_info/shipping_fee_seller_discount', default=0)
            shipping_fee_platform_discount = json_digger(tts_order_raw, 'payment_info/shipping_fee_platform_discount', default=0)

            if not seller_discount_line:
                discount_product = order.mp_account_id.tts_seller_discount_product_id
                if not discount_product:
                    raise ValidationError(
                        'Please define seller discount product on'
                        ' this marketplace account: "%s"' % order.mp_account_id.name)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': discount_product.id,
                        'product_uom_qty': 1,
                        'tax_id': False,
                        # 'discount_amt': seller_discount,
                        'price_unit': -seller_discount,
                        'is_tts_seller_discount': True,
                        'is_promotion_disc_product_line': True
                    })]
                })
            if not platform_discount_line:
                discount_product = order.mp_account_id.tts_platform_discount_product_id
                if not discount_product:
                    raise ValidationError(
                        'Please define platform discount product on'
                        ' this marketplace account: "%s"' % order.mp_account_id.name)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': discount_product.id,
                        'product_uom_qty': 1,
                        'tax_id': False,
                        # 'price_unit': -platform_discount,
                        'is_tts_platform_discount': True,
                        'is_promotion_disc_product_line': True,
                        # 'discount_amt': platform_discount,
                        'price_unit': -platform_discount,
                    })]
                })
            if not shipping_seller_discount_line:
                discount_product = order.mp_account_id.tts_shipping_fee_seller_discount_product_id
                if not discount_product:
                    raise ValidationError(
                        'Please define shipping fee seller discount product on'
                        ' this marketplace account: "%s"' % order.mp_account_id.name)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': discount_product.id,
                        'product_uom_qty': 1,
                        'tax_id': False,
                        # 'discount_amt': shipping_fee_seller_discount,
                        'price_unit': -shipping_fee_seller_discount,
                        'is_tts_shipping_seller_discount': True,
                        'is_promotion_disc_product_line': True
                    })]
                })
            if not shipping_platform_discount_line:
                discount_product = order.mp_account_id.tts_shipping_fee_platform_discount_product_id
                if not discount_product:
                    raise ValidationError(
                        'Please define seller discount product on'
                        ' this marketplace account: "%s"' % order.mp_account_id.name)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': discount_product.id,
                        'product_uom_qty': 1,
                        'tax_id': False,
                        # 'discount_amt': shipping_fee_platform_discount,
                        'price_unit': -shipping_fee_platform_discount,
                        'is_tts_shipping_platform_discount': True,
                        'is_promotion_disc_product_line': True
                    })]
                })
            order._reset_sequence()

    def tiktok_ship_order(self):
        for order in self:
            order.mp_account_id.tiktok_ship_order(order)

    def tiktok_fetch_order(self):
        for order in self:
            order.mp_account_id.tiktok_process_single_order(order.tts_order_id, order)

    def tiktok_print_label(self):
        order_list = []
        url = False
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for order in self:
            res = order.mp_account_id.tiktok_print_label(order)
            if res.get('url'):
                order.mp_awb_url = res.get('url')
                order.mp_awb_datas = base64.b64encode(requests.get(order.mp_awb_url).content)
                order_list.append(str(order.id))

        if order.mp_awb_url:
            if order.mp_account_id.default_awb_action == 'download':
                url = base_url + '/web/binary/tiktok/download_pdf?order_ids=%s' % (','.join(order_list)),

            elif order.mp_account_id.default_awb_action == 'open':
                url = base_url + '/web/binary/tiktok/open_pdf?order_ids=%s' % (','.join(order_list))

            return {
                'name': 'Label',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': url
            }

    def tiktok_reject_order(self):
        mp_account_id = self.mp_account_id
        response = mp_account_id.tiktok_request('get', '/api/reverse/reverse_reason/list', {})

        if response.get('code') == 0:
            reverse_reason_list = response['data']['reverse_reason_list']

            order_reason = []
            for reason in reverse_reason_list:
                if reason.get('available_order_status_list'):
                    if int(self.tts_order_status) in reason['available_order_status_list']:
                        order_reason.append((reason['reverse_reason_key'], reason['reverse_reason']))

            return {
                'name': 'Reject Order(s)',
                'view_mode': 'form',
                'res_model': 'wiz.tiktok.order.reject',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_mp_account_id': mp_account_id.id,
                    'default_mp_order_id': self.mp_invoice_number,
                    'default_order_id': self.id,
                    'default_order_status': self.tts_order_status,
                    'default_order_reason': order_reason,
                },
            }
