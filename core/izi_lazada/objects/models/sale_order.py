# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from itertools import product
from odoo import api, fields, models
import pytz
import bs4
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json
import requests
from base64 import b64decode, b64encode

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.exceptions import ValidationError

from odoo.addons.izi_lazada.objects.utils.lazada.order import LazadaOrder


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    LZ_ORDER_STATUSES = [
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
        ('packed', 'Packed'),
        ('repacked', 'Repacked'),
        ('canceled', 'Canceled'),
        ('ready_to_ship', 'Ready To Ship'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('shipped', 'Shipped'),
        ('failed', 'Failed')
    ]

    lz_order_status = fields.Selection(string="Lazada Order Status", selection=LZ_ORDER_STATUSES, required=False)
    lz_order_id = fields.Char(string="Lazada Order ID", readonly=True)
    lz_invoice_number = fields.Char(string="Lazada Invoice Number")

    @classmethod
    def _add_rec_mp_order_status(cls, mp_order_statuses=None, mp_order_status_notes=None):
        if not mp_order_statuses:
            mp_order_statuses = []
        if not mp_order_status_notes:
            mp_order_status_notes = []

        marketplace, lz_order_status_field = 'lazada', 'lz_order_status'
        lz_order_statuses = {
            'waiting': ['unpaid'],
            'to_cancel': [],
            'cancel': ['canceled'],
            'to_process': ['pending', 'repacked'],
            'in_process': ['packed'],
            'to_ship': ['ready_to_ship'],
            'in_ship': ['shipped'],
            'delivered': [],
            'done': ['delivered'],
            'return': []
        }
        mp_order_statuses.append((marketplace, (lz_order_status_field, lz_order_statuses)))
        mp_order_status_notes.append((marketplace, dict(cls.LZ_ORDER_STATUSES)))
        super(SaleOrder, cls)._add_rec_mp_order_status(mp_order_statuses, mp_order_status_notes)

    # @api.multi
    @api.depends('lz_order_status')
    def _compute_mp_order_status(self):
        super(SaleOrder, self)._compute_mp_order_status()

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'mp_invoice_number': ('order_id', lambda env, r: str(r)),
            'mp_external_id': ('order_id', lambda env, r: str(r)),
            'lz_order_id': ('order_id', lambda env, r: str(r)),
            'lz_order_status': ('statuses', lambda env, r: str(r[-1])),
            'mp_buyer_phone': ('address_billing', lambda env, r: str(r.get('phone'))),
            'mp_recipient_address_city': ('address_billing', lambda env, r: str(r.get('city'))),
            'mp_recipient_address_zipcode': ('address_billing', lambda env, r: str(r.get('post_code'))),
            'mp_recipient_address_phone': ('address_billing', lambda env, r: str(r.get('phone'))),
            'mp_payment_method_info': ('payment_method', None),
            'mp_delivery_carrier_type': ('shipping_info/shipping_provider_type', None),
            'mp_awb_number': ('tracking_code', None),
            'mp_package_id': ('package_id', None),
            'lz_invoice_number': ('invoice_number', lambda env, r: str(r)),
            'mp_cancel_reason': ('reason', None),
        }

        def _get_name_lazada(env, data):
            nameFirst = data.get('first_name')
            nameLast = (" %s" % data.get('last_name')) if (data.get('last_name') != "" and data.get(
                'last_name') != "last_name" and data.get('last_name') != None) else ""
            name = "%s%s" % (nameFirst, nameLast)
            return name

        def _get_name_street(env, data):
            name_street = "%s, %s" % (data.get('address1').replace('*', ''), data.get('post_code'))
            return name_street

        def _get_name_country(env, data):
            name_street = data.get('country')
            return name_street

        def _handle_isoformat_to_dt_str(env, data):
            if data:
                split_data = data.split(' ')
                tz_split = split_data[2].split('00')
                isoformat = '%sT%s%s:00' % (split_data[0], split_data[1], tz_split[0])
                dt = datetime.fromisoformat(isoformat).astimezone(pytz.timezone('UTC'))
                return fields.Datetime.to_string(dt)
            else:
                return None

        def _handle_sla_time(env, data):
            if data:
                dt = datetime.fromisoformat(data).astimezone(pytz.timezone('UTC'))
                return fields.Datetime.to_string(dt)
            else:
                return None

        def _set_mp_delivery_type(env, data):
            mp_delivery_type = None
            if data:
                delivery = data.split(',')[0]
                delivery_type = delivery.split(':')
                if len(delivery_type) > 1:
                    if delivery_type[0] == 'Drop-off':
                        mp_delivery_type = 'drop off'
                    else:
                        mp_delivery_type = 'pickup'
                return mp_delivery_type
            else:
                return None

        def _set_mp_delivery_name(env, data):
            mp_delivery_name = None
            if data:
                delivery = data.split(',')
                if len(delivery) > 1:
                    delivery_name = delivery[1].split(':')
                    if len(delivery_name) > 1:
                        mp_delivery_name = delivery_name[1].strip()
                        return mp_delivery_name
            else:
                return None

        # mapping field dari api return lazada ke table odoo
        # value di isi value api lazada kemudian di samping value ada handler untuk mengubah data.
        mp_field_mapping.update({
            'mp_buyer_username': ('address_billing', _get_name_lazada),
            'mp_buyer_name': ('address_billing', _get_name_lazada),
            'mp_recipient_address_name': ('address_billing', _get_name_lazada),
            'mp_recipient_address_country': ('address_billing', _get_name_country),
            'mp_recipient_address_full': ('address_billing', _get_name_street),
            'mp_order_date': ('created_at', _handle_isoformat_to_dt_str),
            'create_date': ('created_at', _handle_isoformat_to_dt_str),
            'date_order': ('created_at', _handle_isoformat_to_dt_str),
            'mp_order_last_update_date': ('updated_at', _handle_isoformat_to_dt_str),
            'mp_delivery_type': ('shipping_info/shipment_provider', _set_mp_delivery_type),
            'mp_shipping_deadline': ('sla_time_stamp', _handle_sla_time),
            'mp_delivered_deadline': ('sla_time_stamp', _handle_sla_time),
            'mp_pickup_done_time': ('promised_shipping_time', _handle_isoformat_to_dt_str),
            'mp_delivery_carrier_name': ('shipping_info/shipment_provider', _set_mp_delivery_name),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrder, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):

        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()
        order_line_obj = self.env['sale.order.line'].with_context(mp_account_ctx)

        if mp_account.marketplace == 'lazada':
            lz_order_detail_raws, lz_order_detail_sanitizeds = [], []
            for record in records:
                # cek if order in ready_to_ship but pending
                if record.mp_package_id and record.mp_awb_number and record.lz_order_status == 'pending':
                    record.lz_order_status = 'ready_to_ship'

                lz_order_raw = json.loads(record.raw, strict=False)
                list_item_field = ['sku_id', 'name', 'variation',
                                   'item_price', 'paid_price']
                order_line = lz_order_raw['order_line']
                for item in order_line:
                    item['item_info'] = dict([(key, item[key]) for key in list_item_field])
                lz_order_details = [
                    # Insert order_id into tp_order_detail_raw
                    dict(lz_order_detail_raw,
                         **dict([('order_id', record.id)]),
                         **dict([('mp_order_exid', record.mp_external_id)]))
                    for lz_order_detail_raw in json_digger(lz_order_raw, 'order_line')
                ]
                lz_data_raw, lz_data_sanitized = order_line_obj.with_context(
                    mp_account_ctx)._prepare_mapping_raw_data(raw_data=lz_order_details)
                lz_order_detail_raws.extend(lz_data_raw)
                lz_order_detail_sanitizeds.extend(lz_data_sanitized)

            check_existing_records_params = {
                'identifier_field': 'lz_order_item_id',
                'raw_data': lz_order_detail_raws,
                'mp_data': lz_order_detail_sanitizeds,
                'multi': isinstance(lz_order_detail_sanitizeds, list)
            }
            check_existing_records = order_line_obj.with_context(
                mp_account_ctx).check_existing_records(**check_existing_records_params)
            order_line_obj.with_context(
                mp_account_ctx).handle_result_check_existing_records(check_existing_records)
            if self._context.get('skip_error'):
                record_ids_to_unlink = []
                for record in records:
                    sp_order_raw = json.loads(record.raw, strict=False)
                    item_list = sp_order_raw.get('order_line', [])
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

    @api.model
    def _finish_update_records(self, records):
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'lazada':
            for record in records:
                # cek if order in ready_to_ship but pending
                if record.mp_package_id and record.mp_awb_number and record.lz_order_status == 'pending':
                    record.lz_order_status = 'ready_to_ship'
        records = super(SaleOrder, self)._finish_update_records(records)
        return records

    def lazada_generate_delivery_line(self):
        lz_logistic_obj = self.env['mp.lazada.logistic']

        for order in self:
            delivery_line = order.order_line.filtered(lambda l: l.is_delivery)
            lz_order_raw = json.loads(order.raw, strict=False)
            lz_order_shipping = json_digger(lz_order_raw, 'shipping_info')
            lz_logistic_name = lz_order_shipping.get('shipment_provider', False)
            mp_delivery_name = 'LEX ID'
            if lz_logistic_name:
                delivery = lz_logistic_name.split(',')
                if len(delivery) > 1:
                    delivery_name = delivery[1].split(':')
                    if len(delivery_name) > 1:
                        mp_delivery_name = delivery_name[1].strip()
            if not delivery_line:
                lz_logistic = lz_logistic_obj.search([('name', '=ilike', mp_delivery_name)], limit=1)
                if not lz_logistic:
                    lz_logistic = lz_logistic_obj.search([('name', '=ilike', 'LEX ID')], limit=1)
                delivery_product = lz_logistic.get_delivery_product()
                if not delivery_product:
                    raise ValidationError('Please define delivery product on "%s"' % mp_delivery_name)

                # shipping_fee = sp_order_raw.get('actual_shipping_fee', 0)
                # if shipping_fee == 0:
                shipping_fee = lz_order_raw.get('shipping_fee_original', 0)
                order.write({
                    'order_line': [(0, 0, {
                        'sequence': 999,
                        'product_id': delivery_product.id,
                        'name': mp_delivery_name,
                        'product_uom_qty': 1,
                        'price_unit': shipping_fee,
                        'is_delivery': True
                    })]
                })
            else:
                if delivery_line.name != mp_delivery_name:
                    delivery_line.update({
                        'name': mp_delivery_name,
                    })

    def lazada_generate_global_discount_line(self):
        for order in self:
            global_discount_line = order.order_line.filtered(lambda l: l.is_global_discount)
            lz_order_raw = json.loads(order.raw, strict=False)
            shipping_fee_seller_discount = json_digger(lz_order_raw, 'shipping_fee_discount_seller',
                                                       default=0)
            voucher_from_seller = json_digger(lz_order_raw, 'voucher_seller',
                                              default=0)
            voucher_from_lazada = json_digger(lz_order_raw, 'voucher_platform',
                                              default=0)

            total_discount = shipping_fee_seller_discount + voucher_from_seller + voucher_from_lazada
            if not global_discount_line:
                if total_discount > 0:
                    discount_product = order.mp_account_id.global_discount_product_id
                    if not discount_product:
                        raise ValidationError(
                            'Please define global discount product on'
                            ' this marketplace account: "%s"' % order.mp_account_id.name)
                    order.write({
                        'order_line': [(0, 0, {
                            'sequence': 999,
                            'product_id': discount_product.id,
                            'product_uom_qty': 1,
                            'price_unit': -total_discount,
                            'is_global_discount': True
                        })]
                    })
            else:
                if total_discount > 0:
                    global_discount_line.write({
                        'price_unit': total_discount,
                    })

    def lazada_fetch_order(self):
        wiz_mp_order_obj = self.env['wiz.mp.order']

        self.ensure_one()

        wiz_mp_order = wiz_mp_order_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_invoice_number',
            'mp_invoice_number': self.mp_external_id
        })
        return wiz_mp_order.get_order()

    def lazada_set_pack(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                lz_order = LazadaOrder(lz_account)
                order_item_ids = []
                for line in order.order_line:
                    if line.product_type == 'product':
                        split_text = line.lz_order_item_id.split(',')
                        for split in split_text:
                            order_item_ids.append(int(split))
                kwargs = {
                    'order_item_ids': str(order_item_ids),
                    'delivery_type': 'dropship',
                    'shipping_provider': 'LEX ID'
                }

                action_status = lz_order.action_pack_order(**kwargs)
                if action_status == "success":
                    order.lazada_fetch_order()
                    order.action_confirm()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def lazada_set_invoice(self):
        return {
            'name': 'Packed Order',
            'view_mode': 'form',
            'res_model': 'wiz.lz_set_invoice',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_order_ids': [(6, 0, self.ids)],
            },
        }

    def lazada_ready_to_ship(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                lz_order = LazadaOrder(lz_account)
                order_item_ids = []
                for line in order.order_line:
                    if line.product_type == 'product':
                        split_text = line.lz_order_item_id.split(',')
                        for split in split_text:
                            order_item_ids.append(int(split))
                delivery_name = order.mp_delivery_carrier_name.split(',')
                kwargs = {
                    'order_item_ids': str(order_item_ids),
                    'delivery_type': 'dropship',
                    'shipment_provider': delivery_name[0].split(':')[1],
                    'tracking_number': order.mp_awb_number
                }

                action_status = lz_order.action_ready_to_ship(**kwargs)
                if action_status == "success":
                    order.lazada_fetch_order()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def lazada_set_repack(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                lz_order = LazadaOrder(lz_account)
                if order.mp_package_id:
                    kwargs = {
                        'package_id': str(order.mp_package_id),
                    }

                    action_status = lz_order.action_repack(**kwargs)
                    if action_status == "success":
                        order.lazada_fetch_order()
                else:
                    raise ValidationError('Package ID is Not Found, Please Set Pack action for this order')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def lazada_set_delivery(self):
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                lz_order = LazadaOrder(lz_account)
                order_item_ids = []
                for line in order.order_line:
                    if line.product_type == 'product':
                        split_text = line.lz_order_item_id.split(',')
                        for split in split_text:
                            order_item_ids.append(int(split))
                kwargs = {
                    'order_item_ids': str(order_item_ids)
                }
                action_status = lz_order.action_delivery(**kwargs)
                if action_status == "success":
                    order.lazada_fetch_order()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def lazada_print_label(self):
        order_list = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for order in self:
            if order.mp_account_id.mp_token_id.state == 'valid':
                if not order.mp_awb_datas:
                    params = {'access_token': order.mp_account_id.mp_token_id.name}
                    lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                    lz_order = LazadaOrder(lz_account)
                    order_item_ids = []
                    for line in order.order_line:
                        if line.product_type == 'product':
                            split_text = line.lz_order_item_id.split(',')
                            for split in split_text:
                                order_item_ids.append(int(split))
                    kwargs = {
                        'order_item_ids': str(order_item_ids)
                    }
                    lz_response = lz_order.action_print_label(**kwargs)
                    if lz_response['document']:
                        label_string = b64decode(lz_response.get('document').get('file', None)).decode("utf-8")
                        soup = BeautifulSoup(label_string, 'html.parser')
                        iframe = soup.find('iframe')
                        label_url = iframe['src']
                        order.mp_awb_url = label_url
                        order.mp_awb_datas = b64encode(requests.get(order.mp_awb_url).content)

                order_list.append(str(order.id))

        if order.mp_account_id.default_awb_action == 'download':
            return {
                'name': 'Label',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': base_url + '/web/binary/lazada/download_pdf?order_ids=%s' % (','.join(order_list)),
            }
        elif order.mp_account_id.default_awb_action == 'open':
            return {
                'name': 'Label',
                'res_model': 'ir.actions.act_url',
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': base_url + '/web/binary/lazada/open_pdf?order_ids=%s' % (','.join(order_list)),
            }
