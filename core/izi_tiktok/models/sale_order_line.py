# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tts_sale_price = fields.Float(string='Tiktok Sale Price')
    tts_original_price = fields.Float(string='Tiktok Original Price')
    tts_sku_seller_discount = fields.Float(string='Tiktok SKU Seller Discount')
    tts_sku_platform_discount = fields.Float(string='Tiktok SKU PLatform Discount')

    is_tts_seller_discount = fields.Boolean(default=False)
    is_tts_platform_discount = fields.Boolean(default=False)
    is_tts_shipping_seller_discount = fields.Boolean(default=False)
    is_tts_shipping_platform_discount = fields.Boolean(default=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'order_id': ('order_id', None),
            'mp_exid': ('mp_order_exid', None),
            'product_uom_qty': ('quantity', None),
            'tts_original_price': ('sku_original_price', lambda env, r: float(r)),
            'tts_sale_price': ('sku_sale_price', lambda env, r: float(r)),
            'tts_sku_seller_discount': ('sku_seller_discount', lambda env, r: float(r)),
            'tts_sku_platform_discount': ('sku_platform_discount', lambda env, r: float(r)),
            'normal_price': ('sku_original_price', lambda env, r: float(r)),
        }

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_obj = env['mp.product']
            mp_product_variant_obj = env['mp.product.variant']

            product_id = data.get('product_id', False)
            model_id = data.get('sku_id', False)

            product = product_obj
            mp_account_id = env.context.get('mp_account_id')

            mp_product = mp_product_obj.search([
                ('mp_external_id', '=', product_id),
                ('mp_account_id', '=', mp_account_id)
            ], limit=1)
            mp_product_variant = mp_product_variant_obj.search([
                ('mp_external_id', '=', model_id),
                ('mp_account_id', '=', mp_account_id)
            ], limit=1)

            # mp_product = mp_product_obj.search_mp_records('tiktok', product_id)
            # mp_product_variant = mp_product_variant_obj.search_mp_records('tiktok', model_id)

            if mp_product.exists():
                product = mp_product.get_product()
            if mp_product_variant.exists():
                product = mp_product_variant.get_product()
            return product.id

        def _handle_product_sku(env, data):
            sku = None
            if data['item_sku']:
                sku = data['item_sku']
            if data['model_sku']:
                sku = data['model_sku']
            return sku

        def _handle_price_unit(env, data):
            order_component_configs = env['order.component.config'].sudo().search(
                [('active', '=', True), ('mp_account_ids', 'in', env.context.get('mp_account_id'))])
            for component_config in order_component_configs:
                # Process to Remove Product First
                for line in component_config.line_ids:
                    if line.component_type == 'remove_product':
                        if line.remove_discount:
                            return (data['sku_sale_price'] + data['sku_platform_discount'])
            return data['sku_original_price']
        
        def _handle_price_retail(env, data):
            return data['sku_original_price']

        def _handle_price_discount(env, data):
            sku_platform_discount = data['sku_platform_discount'] if data.get('sku_platform_discount') else 0
            return data['sku_original_price'] - (data['sku_sale_price'] + sku_platform_discount)

        def _handle_item_name(env, data):
            name = None
            if data['sku_name']:
                name = '%s (%s)' % (data['product_name'], data['sku_name'])
            else:
                name = '%s' % (data['product_name'])
            return name

        mp_field_mapping.update({
            'product_id': ('item_info', _handle_product_id),
            'price_unit': ('item_info', _handle_price_unit),
            'price_retail': ('item_info', _handle_price_retail),
            'price_discount': ('item_info', _handle_price_discount),
            'mp_product_name': ('item_info', _handle_item_name),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
