# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger

class MPShopeeBrand(models.Model):
    _name = 'mp.shopee.brand'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Brand'

    name = fields.Char(string="Product Brand Name", readonly=True)
    display_name = fields.Char(string="Brand Name", readonly=True)
    brand_id = fields.Integer(string="Shopee Brand ID", readonly=True)
    category_id = fields.Many2one(comodel_name="mp.shopee.category", string="Category ID", required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_external_id': ('brand_id', None),
            'name': ('original_brand_name', None),
            'display_name': ('display_brand_name', None),
            'brand_id': ('brand_id', None),
        }

        def _set_category_brand(env, data):
            mp_category_obj = env['mp.shopee.category']
            mp_category = mp_category_obj.search_mp_records('shopee', data)
            if mp_category:
                return mp_category.id
            return False

        mp_field_mapping.update({
            'category_id': ('category_id', _set_category_brand),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeBrand, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def sp_generate_brand_data(self, mp_brand_raw):
        brand_list = []

        # brand_raw = json_digger(mp_brand_raw, 'category_list')
        # for dat_raw in brand_raw:
        for dat_raw in mp_brand_raw:
            if dat_raw['has_brand']:
                for brand in dat_raw['brand_list']:
                    brand_list.append({
                        'category_id': dat_raw['category_id'],
                        'brand_id': brand.get('brand_id'),
                        'original_brand_name': brand.get('original_brand_name'),
                        'display_brand_name': brand.get('display_brand_name'),
                    })

        return brand_list

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'brand_list': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPShopeeBrand, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values
