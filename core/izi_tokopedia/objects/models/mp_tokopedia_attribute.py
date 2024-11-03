# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger

class MPTokopediaAttribute(models.Model):
    _name = 'mp.tokopedia.attribute'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Attribute'

    name = fields.Char(string="Product Attribute Name", readonly=True)
    display_name = fields.Char(string="Attribute Name", readonly=True)
    sort_order = fields.Integer(string="Sort Order", readonly=True)
    category_id = fields.Many2one(comodel_name="mp.tokopedia.category", string="Category ID", required=False)
    tp_category_id = fields.Integer(string="Tokopedia Category", readonly=True)
    attribute_value_ids = fields.One2many('mp.tokopedia.attribute.value', 'attribute_id', string='Tokopedia Attributes Lines')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'mp_external_id': ('tp_category_id', None),
            'name': ('name', None),
            'display_name': ('name', None),
            'sort_order': ('sort_order', None),
            'tp_category_id': ('category_id', None),
            'attribute_value_ids': ('attribute_value_list', False),
        }

        def _set_category_attribute(env, data):
            mp_category_obj = env['mp.tokopedia.category']
            mp_category = mp_category_obj.search_mp_records('tokopedia', data)
            if mp_category:
                return mp_category.id
            return False

        mp_field_mapping.update({
            'category_id': ('category_id', _set_category_attribute),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPTokopediaAttribute, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tp_generate_attribute_data(self, mp_attribute_raw, mp_account_id):
        attribute_list = []
        # attribute_raw = json_digger(mp_attribute_raw, 'categories')
        if mp_attribute_raw:
            for data in mp_attribute_raw:
                attr_line = [(5, 0)]
                if 'values' in data and data.get('values') != None:
                    attr_line += [(0, 0, {
                        'name': val.get('name'),
                        'display_name': val.get('name'),
                        'value_id': val.get('id'),
                        'value_data': val.get('data'),
                        'mp_external_id': val.get('id'),
                        'mp_account_id': mp_account_id
                    }) for val in data.get("values")]
                attribute_list.append({
                    'category_id': data.get('category_id'),
                    'sort_order': data.get('sort_order'),
                    'name': data.get('variant'),
                    'display_name': data.get('variant'),
                    'attribute_value_list':  attr_line,
                })
        return attribute_list

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'get_attributes': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPTokopediaAttribute, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values


class MPTokopediaAttributeValue(models.Model):
    _name = 'mp.tokopedia.attribute.value'
    _inherit = 'mp.base'
    _description = 'Marketplace Tokopedia Attribute Value'

    name = fields.Char(string="Product Attribute Value Name", readonly=True)
    display_name = fields.Char(string="Attribute Value Name", readonly=True)
    value_id = fields.Integer(string="Value ID", readonly=True)
    value_data = fields.Char(string="Value Data", readonly=True)
    attribute_id = fields.Many2one('mp.tokopedia.attribute', string='Attribute ID')


class MPTokopediaAttributeLine(models.Model):
    _name = 'mp.tokopedia.attribute.line'
    _description = 'Marketplace Tokopedia Attribute Line'

    attribute_id = fields.Many2one('mp.tokopedia.attribute', string='Attribute', readonly=True)
    attribute_value_id = fields.Many2one('mp.tokopedia.attribute.value', string='Value')
    category_id = fields.Many2one('mp.tokopedia.category', string='Category ID')
    tp_product_id = fields.Many2one('mp.product', string='Product ID')
    product_tmpl_id = fields.Many2one('product.template', string='Product ID')
