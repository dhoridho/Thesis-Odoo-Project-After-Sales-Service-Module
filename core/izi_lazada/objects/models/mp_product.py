# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from bs4 import BeautifulSoup


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    lz_item_id = fields.Char(string='Lazada Item ID')
    lz_sku_id = fields.Char(string='Lazada SKU ID')
    lz_has_variant = fields.Boolean(string='Has Variant?')
    lz_brand = fields.Char(string='Lazada Brand')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'name': ('attributes/name', None),
            'default_code': ('attributes/seller_sku', lambda env, r: r.strip() if r else False),
            'weight': ('attributes/weight', lambda env, r: float(r)),
            'length': ('attributes/length', lambda env, r: float(r)),
            'width': ('attributes/width', lambda env, r: float(r)),
            'height': ('attributes/height', lambda env, r: float(r)),
            'mp_external_id': ('item_id', lambda env, r: str(r)),
            'lz_item_id': ('item_id', lambda env, r: str(r)),
            'lz_sku_id': ('attributes/sku_id', lambda env, r: str(r)),
            'lz_item_status': ('status', None),
            'list_price': ('attributes/price', lambda env, r: float(r)),
        }

        def _handle_variant(env, data):
            variant_fields = ['color_family', 'size', 'flavor']
            has_variant = False
            if len(data) > 1:
                return True
            else:
                for fields in variant_fields:
                    if fields in data[0]:
                        has_variant = True
                        break
            return has_variant

        def _handle_product_images(env, data):
            pictures = [(5, 0, 0)]
            for index, pic in enumerate(data):
                base_data_image = {
                    'mp_account_id': env.context['mp_account_id'],
                    'sequence': index,
                    'name': pic,
                }
                pictures.append((0, 0, base_data_image))
            return pictures

        def _handle_item_status(env, data):
            if data:
                if data == 'Active':
                    return True
                else:
                    return False
            return False

        def _handle_description_sale(env, data):
            if data:
                desc_lazada = data.replace(
                    "<br/>", "\n") if "<br/>" in data else data.replace("""<div style="margin: 0;"><span>""", "\n")
                desc_sale = BeautifulSoup(desc_lazada, 'lxml').text
                return desc_sale
            else:
                return None

        mp_field_mapping.update({
            'mp_product_image_ids': ('images', _handle_product_images),
            # 'mp_product_wholesale_ids': ('item_list/wholesales', _handle_wholesale),
            'is_active': ('status', _handle_item_status),
            'lz_has_variant': ('skus', _handle_variant),
            'description_sale': ('attributes/description', _handle_description_sale),

        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)
