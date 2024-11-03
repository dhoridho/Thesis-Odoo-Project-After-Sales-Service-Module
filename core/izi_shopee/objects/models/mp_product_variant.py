# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MPProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    sp_variant_id = fields.Char(string='Shopee Variant External ID')
    sp_variant_image_id = fields.Char(string='Shopee Variant Image ID')
    sp_variant_stock = fields.Integer(string='Shopee Variant Stock')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_external_id': ('sp_variant_id', lambda env, r: str(r)),
            'sp_variant_id': ('sp_variant_id', lambda env, r: str(r).strip()),
            'name': ('name', None),
            'default_code': ('default_code', lambda env, r: r.strip() if r else False),
            'list_price': ('list_price', None),
            'weight': ('weight', lambda env, r: float(r)),
            'sp_variant_image_id': ('image_id', None)
        }

        def _handle_parent_id(env, data):
            mp_product_obj = env['mp.product']
            mp_product = mp_product_obj.search_mp_records('shopee', data)
            if mp_product:
                return mp_product.id
            return None

        def _handle_product_images(env, data):
            if data and env.context.get('store_product_img'):
                return get_mp_asset(data)
            else:
                return None

        def _handle_item_status(env, data):
            if data:
                if data == 'NORMAL':
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
    def sp_generate_variant_data(self, mp_product_raw):
        variant_list = []

        varian_model = json_digger(mp_product_raw, 'variants/model')
        varian_tier = json_digger(mp_product_raw, 'variants/tier_variation')

        def generate_tier_dict(tier_variation):
            tier_dict = {}
            num_attrs = len(tier_variation)
            if num_attrs == 1:
                attr = tier_variation[0]
                for attr_value_index, attr_value in enumerate(attr['option_list']):
                    key = str([attr_value_index])
                    value = {
                        'name': [attr_value.get('option')],
                        'image': attr_value.get('image', {})
                    }
                    tier_dict.update(dict([(key, value)]))
            elif num_attrs == 2:
                first_attr_values = [dict([('name', attr_value.get('option')), ('image', attr_value.get('image', {}))])
                                     for attr_value in tier_variation[0]['option_list']]
                second_attr_values = [dict([('name', attr_value.get('option')), ('image', attr_value.get('image', {}))])
                                      for attr_value in tier_variation[1]['option_list']]
                for first_attr_value_index, first_attr_value in enumerate(first_attr_values):
                    for second_attr_value_index, second_attr_value in enumerate(second_attr_values):
                        key = str([first_attr_value_index, second_attr_value_index])
                        value = {
                            'name': [first_attr_value['name'], second_attr_value['name']],
                            'image': first_attr_value.get('image', {})
                        }
                        tier_dict.update(dict([(key, value)]))
            return tier_dict

        def set_product_attribute(tier_variation):
            attribute = False
            attribute_line = []
            if tier_variation:
                val_name = False
                for res in tier_variation:
                    # attrib = self.env['product.attribute'].sudo().search([('name', '=', res.get("name")), ('is_marketplace', '=', True)], limit=1)
                    attrib = self.env['product.attribute'].sudo().search(
                        [('name', '=', res.get("name"))], limit=1)
                    if not attrib:
                        attribute = self.env['product.attribute'].sudo().create({
                            'name': res.get("name"),
                            'variant_id': 0,
                            'has_unit': 0,
                            'is_primary': 0,
                            'is_marketplace': True
                        }).id
                    else:
                        attribute = attrib.id
                        attrib.sudo().write({
                            'is_primary': 1,
                            'is_marketplace': True
                        })

                    if res.get("option_list"):
                        attribute_val_ids = []
                        for line in res.get("option_list"):
                            val_name = line.get('option')
                            att_val = self.env['product.attribute.value'].sudo().search(
                                [('name', '=', val_name), ('attribute_id', '=', attribute)])
                            if att_val:
                                # attribute_val_ids.append((6, 0, att_val.ids))
                                attribute_val_ids.append(int(att_val.id))
                            else:
                                att_val_id = self.env['product.attribute.value'].sudo().create({
                                    'name': val_name,
                                    'short_name': val_name,
                                    'attribute_id': int(attribute)
                                }).id
                                attribute_val_ids.append(int(att_val_id))
                        attribute_line.append({
                            'attribute_id': int(attribute),
                            'value_ids': attribute_val_ids
                        })
                        self.env['product.attribute'].sudo().write({'value_ids': attribute_val_ids})
                    self.env.cr.commit()
            return attribute_line
            ### ADD product.template.attribute.line
            # self._create_product_template_attribute_line(product_id, response.get("tier_variation"))

        attrib_line = set_product_attribute(varian_tier)
        tier_dict = generate_tier_dict(varian_tier)
        if varian_model:
            for model in varian_model:
                if 'price_info' in model:
                    lst_price = json_digger(model, 'price_info/original_price')[0]
                else:
                    lst_price = 0
                variant_dict = {
                    'mp_product_id': mp_product_raw['item_id'],
                    'weight': mp_product_raw['weight'],
                    'item_status': mp_product_raw['item_status'],
                    'sp_variant_id': json_digger(model, 'model_id'),
                    'list_price': lst_price,
                    'sp_variant_stock': json_digger(model, 'stock_info_v2/seller_stock/stock')[0],
                    'default_code': json_digger(model, 'model_sku') or str(json_digger(model, 'model_id'))
                }

                tier_index = str(json_digger(model, 'tier_index'))
                product_name = mp_product_raw['item_name']
                product_variant_name = product_name+' (%s)' % (', '.join(tier_dict[tier_index]['name']))
                # product_variant_name = product_name + ' (%s)' % (', '.join(tier_dict[tier_index]['name']))
                product_variant_image = tier_dict[tier_index]['image'].get('image_url', None)
                product_variant_image_id = tier_dict[tier_index]['image'].get('image_id', None)

                variant_dict.update({
                    'name': product_variant_name,
                    'image': product_variant_image,
                    'image_id': product_variant_image_id,
                    'variant_line': attrib_line
                })

                variant_list.append(variant_dict)

        return variant_list

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }
