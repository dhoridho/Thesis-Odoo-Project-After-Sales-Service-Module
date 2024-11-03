# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset
from odoo.exceptions import UserError, ValidationError


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    sp_product_id = fields.Char(string='Shopee Product ID', readonly=True)
    sp_item_status = fields.Char(string='Shopee Product Status', readonly=True)
    sp_has_variant = fields.Boolean(string='Shopee is Variant', readonly=True)
    sp_category_id = fields.Many2one('mp.shopee.category', string='Shopee Category', required=False)
    sp_brand_id = fields.Many2one('mp.shopee.brand', string='Shopee Brand', required=False)
    sp_attribute_ids = fields.One2many('mp.shopee.attribute.line', 'sp_product_id', string='Shopee Attribute', ondelete='cascade')
    sp_variant_line = fields.Text('Shopee Attribute Line')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'name': ('item_list/item_name', None),
            'description_sale': ('item_list/description', None),
            # 'default_code': ('item_list/item_sku', lambda env, r: r.strip() if r else False),
            'weight': ('item_list/weight', lambda env, r: float(r)),
            'length': ('item_list/dimension/package_length', lambda env, r: float(r)),
            'width': ('item_list/dimension/package_width', lambda env, r: float(r)),
            'height': ('item_list/dimension/package_height', lambda env, r: float(r)),
            'mp_external_id': ('item_list/item_id', None),
            'sp_product_id': ('item_list/item_id', None),
            'sp_item_status': ('item_list/item_status', None),
            'sp_has_variant': ('item_list/has_model', None),
        }

        def _handle_price_info(env, data):
            if data:
                return data[0].get('original_price')
            else:
                return None

        def _handle_product_images(env, data):
            pictures = [(5, 0, 0)]
            for index, pic in enumerate(data['image_url_list']):
                base_data_image = {
                    'mp_account_id': env.context['mp_account_id'],
                    'mp_external_id': data['image_id_list'][index],
                    'sp_image_id': data['image_id_list'][index],
                    'sequence': index,
                    'name': pic,
                }
                if env.context.get('store_product_img'):
                    base_data_image.update({
                        'image': get_mp_asset(pic)
                    })
                pictures.append((0, 0, base_data_image))
            return pictures

        def _handle_wholesale(env, data):
            if data:
                wholesales = [(5, 0, 0)]
                for wholesale in data:
                    vals = {
                        'mp_account_id': env.context['mp_account_id'],
                        'min_qty': wholesale['min_count'],
                        'max_qty': wholesale['max_count'],
                        'price': wholesale['unit_price'],
                    }
                    wholesales.append((0, 0, vals))
                return wholesales
            return None

        def _handle_item_status(env, data):
            if data:
                if data == 'NORMAL':
                    return True
                else:
                    return False
            return False

        def _set_item_category(env, data):
            mp_category_obj = env['mp.shopee.category']
            mp_category = mp_category_obj.search_mp_records('shopee', data)
            if mp_category:
                return int(mp_category.id)
            return False

        def _set_item_brand(env, data):
            mp_brand_obj = env['mp.shopee.brand']
            mp_brand = mp_brand_obj.search_mp_records('shopee', data)
            if mp_brand:
                return mp_brand.id
            return False

        def _handle_attributes(env, data):
            attribute_obj = env['mp.shopee.attribute']
            attribute_value_obj = env['mp.shopee.attribute.value']
            if data:
                attributes = [(5, 0, 0)]
                for attribute in data:
                    sp_attrib_id = attribute['attribute_id']
                    sp_value_id = attribute['attribute_value_list'][0]['value_id']
                    attribute_ids = attribute_obj.search([('attribute_id', '=', sp_attrib_id)], limit=1)
                    value_ids = attribute_value_obj.search([('value_id', '=', sp_value_id)], limit=1)
                    vals = {
                        'attribute_id': attribute_ids.id,
                        'attribute_value_id': value_ids.id,
                        'category_id': attribute_ids.category_id.id
                    }
                    attributes.append((0, 0, vals))
                return attributes
            return False

        def _handle_default_code(env, data):
            if data:
                if data.get('item_sku'):
                    product_code = data.get('item_sku')
                else:
                    product_code = data.get('item_id')
                return product_code
            return False

        mp_field_mapping.update({
            'default_code': ('item_list', _handle_default_code),
            'list_price': ('item_list/price_info', _handle_price_info),
            'mp_product_image_ids': ('item_list/image', _handle_product_images),
            'mp_product_wholesale_ids': ('item_list/wholesales', _handle_wholesale),
            'is_active': ('item_list/item_status', _handle_item_status),
            'sp_category_id': ('item_list/category_id', _set_item_category),
            'sp_brand_id': ('item_list/brand/brand_id', _set_item_brand),
            'sp_attribute_ids': ('item_list/attribute_list', _handle_attributes),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def create(self, values):
        if 'marketplace' in values and values.get('marketplace') == 'shopee':
            if 'sp_category_id' in values and not values.get('sp_category_id'):
                raise ValidationError('Shopee: Category not found')
        return super(MarketplaceProduct, self).create(values)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'product_info': default_sanitizer
        }

    @api.onchange('sp_category_id')
    def _onchange_set_attribute_mp_product(self):
        for res in self:
            if res.sp_category_id:
                attribute_line = [(5, 0)]
                attrib_line_obj = self.env['mp.shopee.attribute.line'].search([('category_id', '=', res.sp_category_id.id), ('sp_product_id', '=', res.id)])
                res.sp_attribute_ids = False
                if attrib_line_obj:
                    attribute_line += [(0, 0, {
                        'attribute_id': rec.attribute_id.id,
                        'attribute_value_id': rec.attribute_value_id.id,
                        'category_id': rec.category_id.id,
                        'sp_product_id': rec.sp_product_id.id
                    }) for rec in attrib_line_obj]
                    res.sp_attribute_ids = attribute_line
                else:
                    attrib_obj = self.env['mp.shopee.attribute'].search([('category_id', '=', res.sp_category_id.id)])
                    if attrib_obj:
                        attribute_line += [(0, 0, {
                            'attribute_id': rec.id,
                            'attribute_value_id': False,
                            'category_id': res.sp_category_id.id,
                            'sp_product_id': res.id
                        }) for rec in attrib_obj]
                        res.sp_attribute_ids = attribute_line
            else:
                res.sp_attribute_ids = False
