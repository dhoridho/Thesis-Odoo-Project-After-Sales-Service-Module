# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    tp_variant_id = fields.Char(string="Tokopedia Product Variant ID", readonly=True)
    tp_variant_image_id = fields.Char(string='Product Variant Image ID')
    tp_variant_stock = fields.Integer(string='Tokopedia Variant Stock')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'mp_external_id': ('basic/productID', lambda env, r: str(r)),
            'tp_variant_id': ('basic/productID', lambda env, r: str(r)),
            'name': ('basic/name', None),
            'default_code': ('other/sku', lambda env, r: r.strip() if r else False),
            'list_price': ('price/value', None),
            'weight': ('weight/value', None),
            'length': ('volume/length', None),
            'width': ('volume/width', None),
            'height': ('volume/height', None),
            'tp_variant_stock': ('stock/value', None),
            'image': ('pictures/OriginalURL',
                      lambda env, r: get_mp_asset(r[0]) if env.context.get('store_product_img') else None),
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('tokopedia', data)
            if mp_product:
                return mp_product.id
            return None
            
        def _handle_item_status(env, data):
            if data:
                if data == 1:
                    return True
                else:
                    return False
            return False

        mp_field_mapping.update({
            'mp_product_id': ('variant/parentID', _handle_parent_id),
            'is_active': ('basic/status', _handle_item_status)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProductVariant, cls)._add_rec_mp_field_mapping(mp_field_mappings)


    # ### penambahan function baru
    # @api.model
    def tp_generate_variant_data(self, mp_product_raw):
        variant_list = []

        varian_model = json_digger(mp_product_raw, 'variant_details')
        varian_tier = json_digger(mp_product_raw, 'variant_id_combinations')

        tp_category_id = self._set_category_variant(json_digger(mp_product_raw, 'category_id'))

        attrib_line = self.set_product_attribute(varian_model)

        for model in varian_model:
            variant_dict = {
                'category_id': json_digger(mp_product_raw, 'category_id'),
                'tp_variant_id': json_digger(model, 'variant_id'),
                'variant_line': attrib_line,
            }
            variant_list.append(variant_dict)

        return variant_list

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }

    def _set_category_variant(self, category_id):
        mp_category_obj = self.env['mp.tokopedia.category']
        mp_category = mp_category_obj.search_mp_records('tokopedia', category_id)
        if mp_category:
            return mp_category.id
        return False

    def set_product_attribute(self, tier_variation):
        attribute = False
        attribute_line = []
        attribute_unit_line = []
        attribute_value_line = []
        if tier_variation:
            val_name = False
            for res in tier_variation:
                # attrib = self.env['product.attribute'].sudo().search([('name', '=', res.get("name")), ('variant_id', '=', res.get("variant_id"))])
                # attrib = self.env['product.attribute'].sudo().search(
                #     [('name', '=', res.get("name")), ('is_marketplace', '=', True)], limit=1)
                attrib = self.env['product.attribute'].sudo().search(
                    [('name', '=', res.get("name"))], limit=1)
                if not attrib:
                    attribute = self.env['product.attribute'].sudo().create({
                        'name': res.get("name"),
                        'variant_id': res.get("variant_id"),
                        'has_unit': res.get("has_unit"),
                        'identifier': res.get("identifier"),
                        'status': res.get("status"),
                        'is_primary': res.get("is_primary"),
                        'is_marketplace': True
                    }).id
                else:
                    attribute = attrib.id
                    if attrib.variant_id == res.get("variant_id"):
                        attribute = attrib.id
                    else:
                        attrib.sudo().write({
                            'variant_id': res.get("variant_id"),
                            'has_unit': res.get("has_unit"),
                            'identifier': res.get("identifier"),
                            'status': res.get("status"),
                            'is_primary': res.get("is_primary"),
                            'is_marketplace': True
                        })
                attribute_unit_ids = []
                if res.get("units"):
                    for unit in res.get("units"):
                        att_unit_id = False
                        if unit.get("variant_unit_id") > 0:
                            unit_name = unit.get('unit_name')
                            att_unit = self.env['product.attribute.unit'].sudo().search(
                                [('name', '=', unit_name), ('attribute_id', '=', attribute)])
                            if att_unit:
                                # attribute_val_ids.append((6, 0, att_val.ids))
                                attribute_unit_ids.append(int(att_unit.id))
                                att_unit_id = att_unit.id
                            else:
                                att_unit_id = self.env['product.attribute.unit'].sudo().create({
                                    'name': unit_name,
                                    'short_name': unit.get("unit_short_name"),
                                    'status': unit.get("status"),
                                    'unit_id': unit.get("variant_unit_id"),
                                    'attribute_id': int(attribute)
                                }).id
                                attribute_unit_ids.append(int(att_unit_id))
                        attribute_val_ids = []
                        if unit.get("unit_values"):
                            for line in unit.get("unit_values"):
                                val_name = line.get('value')
                                att_val = self.env['product.attribute.value'].sudo().search(
                                    [('name', '=', val_name), ('attribute_id', '=', attribute)])
                                if att_val:
                                    # attribute_val_ids.append((6, 0, att_val.ids))
                                    attribute_val_ids.append(int(att_val.id))
                                    att_val_id = att_val.id
                                else:
                                    att_val_id = self.env['product.attribute.value'].sudo().create({
                                        'name': val_name,
                                        'short_name': val_name,
                                        'sequence': line.get("equivalent_value_id"),
                                        'english_name': line.get("english_value"),
                                        'unit_value_id': line.get("variant_unit_value_id"),
                                        'status': line.get("status"),
                                        'hex': line.get("hex"),
                                        'icon': line.get("icon"),
                                        'attribute_unit_id': att_unit_id,
                                        'attribute_id': int(attribute)
                                    }).id
                                    attribute_val_ids.append(int(att_val_id))
                                attribute_value_line.append({
                                    'value_id': attribute_val_ids
                                })
                        attribute_unit_line.append({
                            'unit_id': attribute_unit_ids,
                            'attribute_value_id': attribute_value_line
                        })
                attribute_line.append({
                    'attribute_id': int(attribute),
                    'attribute_unit_id': attribute_unit_line
                })
                # self.env['product.attribute'].sudo().write({'value_ids': attribute_val_ids})
        return attribute_line