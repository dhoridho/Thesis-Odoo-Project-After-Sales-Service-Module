# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class MPShopeeCategory(models.Model):
    _name = 'mp.shopee.category'
    _inherit = 'mp.base'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'display_name'
    _order = 'display_name'
    _description = 'Marketplace Shopee Category'

    name = fields.Char(string="Product Category Name", readonly=True)
    display_name = fields.Char(string="Category Name", compute='_compute_complete_name', store=True)
    # parent_id = fields.Integer("Parent Category ID")
    parent_id = fields.Many2one('mp.shopee.category', 'Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    has_children = fields.Boolean(default=False)
    child_id = fields.One2many('mp.shopee.category', 'parent_id', 'Child Categories')
    category_id = fields.Integer(string="Shopee Category ID", readonly=True)
    parent_category_id = fields.Integer(string="Shopee Parent Category ID", readonly=True)
    has_brand = fields.Boolean(default=False)
    attribute_mapped = fields.Boolean(default=False)
    brand_mapped = fields.Boolean(default=False)

    @api.depends('name', 'parent_id.display_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.display_name = '%s / %s' % (category.parent_id.display_name, category.name)
            else:
                category.display_name = category.name

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError('You cannot create recursive categories.')
        return True

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'shopee'
        mp_field_mapping = {
            'mp_external_id': ('category_list/category_id', None),
            'name': ('category_list/original_category_name', None),
            'display_name': ('category_list/display_category_name', None),
            'has_children': ('category_list/has_children', None),
            'category_id': ('category_list/category_id', None),
            'parent_category_id': ('category_list/parent_category_id', None),
            'has_brand': ('category_list/has_brand', None),
        }

        def _set_category_parent(env, data):
            mp_category_obj = env['mp.shopee.category']
            mp_category = mp_category_obj.search_mp_records('shopee', data)
            if mp_category:
                return mp_category.id
            return False

        mp_field_mapping.update({
            'parent_id': ('category_list/parent_category_id', _set_category_parent),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPShopeeCategory, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def shopee_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'category_list': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPShopeeCategory, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values
