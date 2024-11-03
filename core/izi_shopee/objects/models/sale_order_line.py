# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_shopee_coins = fields.Boolean(string="Is a Shopee Coins", default=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'order_id': ('order_id', None),
            'mp_exid': ('mp_order_exid', None),
            'sp_weight': ('weight', None),
            'product_uom_qty': ('model_quantity_purchased', None),
            'sp_discounted_price': ('model_discounted_price', None),
            'sp_original_price': ('model_original_price', None),
            'normal_price': ('model_original_price', None),
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
                            if data['model_discounted_price'] == 0 and data['promotion_type'] == 'bundle_deal':
                                promotion = env['mp.promotion.program'].sudo().search(
                                    [('mp_external_id', '=', str(data['promotion_id']))], limit=1)
                                if promotion.exists():
                                    if promotion.sp_bundle_discount_percentage > 0:
                                        discount_price = data['model_original_price'] * \
                                            promotion.sp_bundle_discount_percentage/100
                                        final_discounted_price = data['model_original_price'] - discount_price
                                        return final_discounted_price
                                    elif promotion.sp_bundle_discount_value > 0:
                                        final_discounted_price = data['model_original_price'] - \
                                            promotion.sp_bundle_discount_value
                                        return final_discounted_price
                                    elif promotion.sp_bundle_fix_price > 0:
                                        return promotion.sp_bundle_fix_price
                                else:
                                    return data['model_discounted_price']
                            else:
                                return data['model_discounted_price']
            return data['model_original_price']

        def _handle_item_name(env, data):
            name = None
            if data['model_name']:
                name = '%s (%s)' % (data['item_name'], data['model_name'])
            else:
                name = '%s' % (data['item_name'])
            return name

        def _handle_item_sku(env, data):
            name = None
            if data['model_sku']:
                return data['model_sku']
            else:
                return data['item_sku']

        mp_field_mapping.update({
            'product_id': ('item_info', _handle_product_id),
            'sp_sku': ('item_info', _handle_product_sku),
            'price_unit': ('item_info', _handle_price_unit),
            'mp_product_name': ('item_info', _handle_item_name),
            'mp_product_sku': ('item_info', _handle_item_sku),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
