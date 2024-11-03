# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime
import time
import json
from odoo import api, fields, models, tools

from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


class MarketplaceReturn(models.Model):
    _inherit = 'mp.return'

    _SP_RETURN_STATUSES = [
        ('REQUESTED', 'In Reuqested'),
        ('ACCEPTED', 'In Accepeted'),
        ('CANCELLED', 'In Cancelled'),
        ('JUDGING', 'In Judging'),
        ('REFUND_PAID', 'Refund Paid'),
        ('CLOSED', 'In Closed'),
        ('PROCESSING', 'In Processing'),
        ('SELLER_DISPUTE', 'Seller Dispute'),
    ]

    _SP_RETURN_REASON = [
        ('NONE', 'None'),
        ('NOT_RECEIPT', 'Not Receipt'),
        ('WRONG_ITEM', 'Wrong Item'),
        ('ITEM_DAMAGED', 'Item Damaged'),
        ('DIFFERENT_DESCRIPTION', 'Diferent Description'),
        ('MUTUAL_AGREE', 'Mutual Agree'),
        ('OTHER', 'Other'),
        ('CHANGE_MIND', 'Change Mind'),
        ('ITEM_MISSING', 'Item Misiing'),
        ('EXPECTATION_FAILED', 'Expectation Failed'),
        ('ITEM_FAKE', 'Item Fake'),
        ('PHYSICAL_DMG', 'Physical Damage'),
        ('FUNCTIONAL_DMG', 'Functional Damage'),
    ]

    _SP_SELLER_PROOF_STATUS = [
        ('PENDING', 'Pending'),
        ('UPLOADED', 'Uploaded'),
        ('OVERDUE', 'Overdue'),
    ]

    _SP_SELLER_COMPENSATION_STATUS = [
        ('PENDING_RESPOND', 'Pending Repond'),
        ('PENDING_REQUEST', 'Pending Request'),
        ('NOT_REQUIRED', 'Not Reuqested'),
        ('REQUESTED', 'Requested'),
        ('TERMINATED', 'Terminated'),
        ('REQUEST_APPROVED', 'Requested Approved'),
        ('REQUEST_REJECTED', 'Requested Rejected'),
        ('REQUEST_CANCELLED', 'Requested Cancelled'),
    ]

    _SP_NEGOTIATION_STATUS = [
        ('PENDING_RESPOND', 'Pending Repond'),
        ('PENDING_BUYER_RESPOND', 'Pending Buyer Respond'),
        ('TERMINATED', 'Terminated'),
    ]

    sp_return_status = fields.Selection(string="Shopee Return Status", selection=_SP_RETURN_STATUSES)
    sp_return_reason = fields.Selection(string="Shopee Return Reason", selection=_SP_RETURN_REASON)
    sp_seller_proof_status = fields.Selection(string="Seller Proof Status", selection=_SP_SELLER_PROOF_STATUS)
    sp_seller_compensation_status = fields.Selection(
        string="Seller Compensation Status", selection=_SP_SELLER_COMPENSATION_STATUS)
    sp_negotitation_status = fields.Selection(string="Seller Negotitation Status", selection=_SP_NEGOTIATION_STATUS)
    sp_return_sn = fields.Char(string="Shopee Return SN")
    sp_tracking_number = fields.Char(string="Shopee Tracking Number")
    sp_amount_before_discount = fields.Float(string='Amount Before Discount')

    @classmethod
    def _add_rec_mp_return_status(cls, mp_return_statuses=None):
        if not mp_return_statuses:
            mp_return_statuses = []

        marketplace, sp_return_status_field = 'shopee', 'sp_return_status'
        sp_return_statuses = {
            'in_requested': ['REQUESTED'],
            'in_process': ['ACCEPTED', 'JUDGING', 'PROCESSING'],
            'completed': ['REFUND_PAID', 'SELLER_DISPUTE'],
            'closed': ['CANCELLED', 'CLOSED'],
        }
        mp_return_statuses.append((marketplace, (sp_return_status_field, sp_return_statuses)))
        super(MarketplaceReturn, cls)._add_rec_mp_return_status(mp_return_statuses)

    # @api.multi
    @api.depends('sp_return_status')
    def _compute_mp_return_status(self):
        super(MarketplaceReturn, self)._compute_mp_return_status()

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_return_sn': ('return_sn', lambda env, r: str(r)),
            'mp_external_id': ('return_sn', lambda env, r: str(r)),
            'sp_return_sn': ('return_sn', lambda env, r: str(r)),
            'sp_return_status': ('status', None),
            'sp_return_reason': ('reason', None),
            'mp_order_exid': ('order_sn', lambda env, r: str(r)),
            'mp_return_reason': ('text_reason', None),
            'sp_negotiation_status': ('negotiation/negotiation_status', None),
            'sp_seller_compensation_status': ('negotiation/negotiation_status', None),
            'sp_seller_proof_status': ('seller_proof/seller_proof_status', None),
            'mp_return_amount': ('refund_amount', lambda env, r: float(r) if r else None),
            'sp_amount_before_discount': ('amount_before_discount', lambda env, r: float(r) if r else None),
            'mp_user_name': ('user/username', None)
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _handle_return_images(env, data):
            pictures = [(5, 0, 0)]
            for index, pic in enumerate(data):
                base_data_image = {
                    'sequence': index,
                    'name': pic,
                    'image': get_mp_asset(pic)
                }
                pictures.append((0, 0, base_data_image))
            return pictures

        mp_field_mapping.update({
            'mp_return_image_ids': ('image', _handle_return_images),
            'mp_return_create_time': ('create_time', _convert_timestamp_to_datetime),
            'mp_return_update_time': ('update_time', _convert_timestamp_to_datetime),
            'mp_return_ship_due_date': ('due_date', _convert_timestamp_to_datetime),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceReturn, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    def shopee_process_return_line(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()
        return_line_obj = self.env['mp.return.line'].with_context(mp_account_ctx)
        sp_return_line_raws, sp_return_line_sanitizeds = [], []
        for record in records:
            sp_return_raw = json.loads(record.raw, strict=False)
            list_item_field = ['item_id', 'model_id', 'item_sku', 'variation_sku']
            item_list = sp_return_raw['item']
            for item in item_list:
                item['item_info'] = dict([(key, item[key]) for key in list_item_field])

            sp_return_lines = [
                # Insert order_id into tp_order_detail_raw
                dict(sp_return_line_raw,
                     **dict([('mp_return_id', record.id)]),
                     **dict([('mp_return_exid', record.mp_return_sn)]))
                for sp_return_line_raw in json_digger(sp_return_raw, 'item')
            ]
            sp_data_raw, sp_data_sanitized = return_line_obj.with_context(
                mp_account_ctx)._prepare_mapping_raw_data(raw_data=sp_return_lines)
            sp_return_line_raws.extend(sp_data_raw)
            sp_return_line_sanitizeds.extend(sp_data_sanitized)

        def identify_return_line(record_obj, values):
            return record_obj.search([('mp_return_id', '=', values['mp_return_id']),
                                      ('product_id', '=', values['product_id'])], limit=1)

        check_existing_records_params = {
            'identifier_method': identify_return_line,
            'raw_data': sp_return_line_raws,
            'mp_data': sp_return_line_sanitizeds,
            'multi': isinstance(sp_return_line_sanitizeds, list)
        }
        check_existing_records = return_line_obj.with_context(
            mp_account_ctx).check_existing_records(**check_existing_records_params)
        return_line_obj.with_context(
            mp_account_ctx).handle_result_check_existing_records(check_existing_records)
        # if self._context.get('skip_error'):
        #     record_ids_to_unlink = []
        #     for record in records:
        #         sp_order_raw = json.loads(record.raw, strict=False)
        #         item_list = sp_order_raw.get('item_list', [])
        #         record_line = record.order_line.mapped('product_type')
        #         if not record_line:
        #             record_ids_to_unlink.append(record.id)
        #         elif 'product' not in record_line:
        #             record_ids_to_unlink.append(record.id)
        #         elif len(item_list) != record_line.count('product'):
        #             record_ids_to_unlink.append(record.id)

        #     records.filtered(lambda r: r.id in record_ids_to_unlink).unlink()
        return records

    @api.model
    def _finish_create_records(self, records):
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'shopee':
            records = self.shopee_process_return_line(records)
        records = super(MarketplaceReturn, self)._finish_create_records(records)
        return records

    @api.model
    def _finish_update_records(self, records):
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'shopee':
            records = self.shopee_process_return_line(records)
        records = super(MarketplaceReturn, self)._finish_update_records(records)
        return records

    def shopee_fetch_order_return(self):
        wiz_mp_order_obj = self.env['wiz.mp.order.return']
        self.ensure_one()

        wiz_mp_order = wiz_mp_order_obj.create({
            'mp_account_id': self.mp_account_id.id,
            'params': 'by_mp_return_number',
            'mp_return_number': self.mp_return_sn
        })
        return wiz_mp_order.get_return()


class MarketplaceReturnLine(models.Model):
    _inherit = 'mp.return.line'

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_return_id': ('mp_return_id', None),
            'mp_item_price': ('item_price', None),
            'mp_item_qty': ('amount', None),
        }

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']

            product_id = data.get('item_id', False)
            model_id = data.get('model_id', False)

            product = product_obj
            mp_product = mp_product_obj.search_mp_records('shopee', product_id)
            mp_product_variant = mp_product_variant_obj.search_mp_records('shopee', model_id)

            if mp_product.exists():
                product = mp_product.get_product()
            if mp_product_variant.exists():
                product = mp_product_variant.get_product()

            return product.id

        def _handle_product_sku(env, data):
            sku = None
            if data['item_sku']:
                sku = data['item_sku']
            if data['variation_sku']:
                sku = data['variation_sku']
            return sku

        mp_field_mapping.update({
            'product_id': ('item_info', _handle_product_id),
            'default_code': ('item_info', _handle_product_sku),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceReturnLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
