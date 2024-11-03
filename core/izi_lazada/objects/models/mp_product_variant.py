# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MPProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    lz_variant_id = fields.Char(string='Product Variant External ID')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'mp_external_id': ('lz_variant_id', lambda env, r: str(r)),
            'lz_variant_id': ('lz_variant_id', lambda env, r: str(r)),
            'name': ('name', None),
            'default_code': ('default_code', lambda env, r: r.strip() if r else None),
            'list_price': ('list_price', lambda env, r: float(r)),
            'weight': ('weight', lambda env, r: float(r)),
            'mp_product_variant_main_image_url': ('image', None),
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('lazada', data)
            if mp_product:
                return mp_product.id
            return None

        def _handle_product_images(env, data):
            if data:
                if env.context.get('store_product_img'):
                    return get_mp_asset(data)
                else:
                    return None
            else:
                return None

        def _handle_item_status(env, data):
            if data:
                if data == 'active':
                    return True
                else:
                    return False
            return False

        mp_field_mapping.update({
            'image': ('image', _handle_product_images),
            'mp_product_id': ('mp_product_id', _handle_parent_id),
            'is_active': ('item_status', _handle_item_status)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPProductVariant, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def lz_generate_variant_data(self, mp_product_raw):
        variant_list = []
        variant_fields = ['flavor', 'color_family', 'size']
        varian_data = json_digger(mp_product_raw, 'skus')

        for variant in varian_data:
            variant_value = []
            for k, v in variant.items():
                if k in variant_fields:
                    variant_value.append(v)

            variant_dict = {
                'mp_product_id': mp_product_raw.get('item_id'),
                'weight': variant.get('package_weight'),
                'item_status': variant.get('Status'),
                'lz_variant_id': variant.get('SkuId', None),
                'list_price': variant.get('price'),
                'default_code': variant.get('SellerSku', None),
            }

            product_name = mp_product_raw['attributes']['name']
            product_variant_name = product_name+' - %s' % (','.join(variant_value))
            product_image = False
            if variant.get('Images', False):
                product_image = variant['Images'][0]
            variant_dict.update({
                'name': product_variant_name,
                'image': product_image
            })

            variant_list.append(variant_dict)

        return variant_list
