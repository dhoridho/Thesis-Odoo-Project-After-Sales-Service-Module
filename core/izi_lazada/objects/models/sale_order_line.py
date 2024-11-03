# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lz_order_item_id = fields.Text(string="Lazada Order Item ID",
                                   help='This is can multiple id, separator with comma (,)')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'order_id': ('order_id', lambda env, r: int(r)),
            'mp_exid': ('mp_order_exid', None),
            'lz_order_item_id': ('order_item_ids', lambda env, r: str(r)),
            'mp_external_id': ('order_item_ids', lambda env, r: str(r)),
            'product_uom_qty': ('qty', lambda env, r: int(r)),
        }

        def _handle_product_id(env, data):
            product_obj = env['product.product']
            mp_product_variant_obj = env['mp.product.variant']
            mp_product_obj = env['mp.product']

            sku_id = data.get('sku_id', False)
            product_id = data.get('product_id', False)

            product = product_obj
            if sku_id:
                domain = [('lz_sku_id', '=', sku_id), ('mp_account_id', '=', env.context.get('mp_account_id'))]
                mp_product = mp_product_obj.search(domain, limit=1)
                mp_product_variant = mp_product_variant_obj.search_mp_records('lazada', sku_id)

            if mp_product_variant.exists():
                product = mp_product_variant.get_product()
            elif mp_product.exists():
                product = mp_product.get_product()
            return product.id

        def _handle_price_unit(env, data):
            order_component_configs = env['order.component.config'].sudo().search(
                [('active', '=', True), ('mp_account_ids', 'in', env.context.get('mp_account_id'))])
            for component_config in order_component_configs:
                # Process to Remove Product First
                for line in component_config.line_ids:
                    if line.component_type == 'remove_product':
                        if line.remove_discount:
                            return data['paid_price']

            return data.get('item_price')

        def _handle_item_name(env, data):
            name = None
            if data['variation']:
                variant_name = []
                variant = data['variation'].split(',')
                for var in variant:
                    variant_name.append(var.split(':')[-1])
                name = '%s (%s)' % (data['name'], ','.join(variant_name))
            else:
                name = '%s' % (data['name'])
            return name

        mp_field_mapping.update({
            'product_id': ('item_info', _handle_product_id),
            'price_unit': ('item_info', _handle_price_unit),
            'normal_price': ('item_info/item_price', lambda env, r: float(r) if r else 0.0),
            'mp_product_name': ('item_info', _handle_item_name),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(SaleOrderLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
