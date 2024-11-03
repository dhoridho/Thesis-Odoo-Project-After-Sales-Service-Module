# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger

class MPShopeeAttribute(models.Model):
    _name = 'mp.shopee.attribute'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Attribute'

    name = fields.Char(string="Product Attribute Name", readonly=True)
    display_name = fields.Char(string="Attribute Name", readonly=True)
    attribute_id = fields.Integer(string="Shopee Attribute ID", readonly=True)
    category_id = fields.Many2one(comodel_name="mp.shopee.category", string="Category ID", required=False)
    is_mandatory = fields.Boolean("is Mandatory")
    input_validation_type = fields.Char(string="Input Validation Type", readonly=True)
    format_type = fields.Char(string="Format Type", readonly=True)
    date_format_type = fields.Char(string="Date Format Type", readonly=True)
    input_type = fields.Char(string="Input Type", readonly=True)
    attribute_unit = fields.Char(string="Attribute Unit", readonly=True)
    attribute_value_ids = fields.One2many('mp.shopee.attribute.value', 'attribute_id', string='Shopee Attributes Lines')


    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_external_id': ('attribute_id', None),
            'name': ('original_attribute_name', None),
            'display_name': ('display_attribute_name', None),
            'attribute_id': ('attribute_id', None),
            'is_mandatory': ('is_mandatory', None),
            'input_validation_type': ('input_validation_type', None),
            'format_type': ('format_type', None),
            'date_format_type': ('date_format_type', None),
            'input_type': ('input_type', None),
            'attribute_unit': ('attribute_unit', None),
            'attribute_value_ids': ('attribute_value_list', False),
        }

        def _set_category_attribute(env, data):
            mp_category_obj = env['mp.shopee.category']
            mp_category = mp_category_obj.search_mp_records('shopee', data)
            if mp_category:
                return mp_category.id
            return False

        mp_field_mapping.update({
            'category_id': ('category_id', _set_category_attribute),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeAttribute, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def sp_generate_attribute_data(self, mp_attribute_raw, mp_account_id):
        attribute_list = []
        attribute_value_obj = self.env['mp.shopee.attribute.value']
        # attribute_raw = json_digger(mp_attribute_raw, 'category_list')
        # for dat_raw in attribute_raw:
        for dat_raw in mp_attribute_raw:
            if dat_raw['has_attribute']:
                for attr in dat_raw['attribute_list']:
                    attr_line = []
                    if 'attribute_value_list' in attr:
                        for val in attr.get("attribute_value_list"):
                            attribute_value_ids = attribute_value_obj.search([('value_id', '=', val.get('value_id'))])
                            if attribute_value_ids:
                                attr_line.append((6, 0, attribute_value_ids.ids))
                            else:
                                attr_line.append((0, 0, {
                                    'name': val.get('original_value_name'),
                                    'display_name': val.get('display_value_name'),
                                    'value_id': val.get('value_id'),
                                    'value_unit': val.get('value_unit'),
                                    'mp_external_id': val.get('value_id'),
                                    'mp_account_id': mp_account_id,
                                }))
                    attribute_list.append({
                        'category_id': dat_raw['category_id'],
                        'attribute_id': attr.get('attribute_id'),
                        'original_attribute_name': attr.get('original_attribute_name'),
                        'display_attribute_name': attr.get('display_attribute_name'),
                        'is_mandatory': attr.get('is_mandatory'),
                        'input_validation_type': attr.get('input_validation_type'),
                        'format_type': attr.get('format_type'),
                        'date_format_type': attr.get('date_format_type'),
                        'input_type': attr.get('input_type'),
                        'attribute_unit': attr.get('attribute_unit'),
                        'attribute_value_list':  attr_line,
                    })
                    # 'attribute_value_list': attr.get('attribute_value_list'),
        return attribute_list

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'attribute_list': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPShopeeAttribute, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values


class MPShopeeAttributeValue(models.Model):
    _name = 'mp.shopee.attribute.value'
    _inherit = 'mp.base'
    _description = 'Marketplace Shopee Attribute Value'

    name = fields.Char(string="Product Attribute Value Name")
    display_name = fields.Char(string="Attribute Value Name")
    value_id = fields.Integer(string="Value ID", readonly=True, default=0)
    value_unit = fields.Char(string="Value Unit", readonly=True)
    parent_attribute_id = fields.Integer(string="Parent Attribute ID", readonly=True)
    parent_value_id = fields.Integer(string="Parent Value ID", readonly=True)
    parent_brand_id = fields.Integer(string="Parent Brand ID", readonly=True)
    attribute_id = fields.Many2one('mp.shopee.attribute', string='Attribute ID')


class MPShopeeAttributeLine(models.Model):
    _name = 'mp.shopee.attribute.line'
    _description = 'Marketplace Shopee Attribute Line'

    attribute_id = fields.Many2one('mp.shopee.attribute', string='Attribute', store=True)
    attribute_value_id = fields.Many2one('mp.shopee.attribute.value', string='Value')
    category_id = fields.Many2one('mp.shopee.category', string='Category ID')
    sp_product_id = fields.Many2one('mp.product', string='Product ID')
    product_tmpl_id = fields.Many2one('product.template', string='Product ID')
    sp_attribute_name = fields.Char(string='SP Attribute Name', compute='_compute_shopee_name_mandatory', readonly=True)
    is_mandatory = fields.Boolean(string='SP Mandatory', compute='_compute_shopee_name_mandatory', readonly=True)

    @api.depends('attribute_id')
    def _compute_shopee_name_mandatory(self):
        for rec in self:
            if rec.attribute_id:
                rec.is_mandatory = rec.attribute_id.is_mandatory
                rec.sp_attribute_name = rec.attribute_id.name

