# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger


class MPProductCategory(models.Model):
    _name = 'mp.tiktok.product.category'
    _inherit = 'mp.base'
    # _rec_name = 'product_category'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'display_name'
    _order = 'display_name'
    _description = 'Marketplace Tiktok Category'

    name = fields.Char(string="Tiktok Category Name", readonly=True)
    display_name = fields.Char(string="Tiktok Display Name", compute='_compute_complete_name', store=True)
    category_id = fields.Char(string="Tiktok Category ID", readonly=True)
    # parent_id = fields.Char(string="Tiktok Parent ID", readonly=True)
    # local_display_name = fields.Char(string="Tiktok Local Name", readonly=True)
    is_leaf = fields.Boolean(string="Is Leaf", readonly=True)
    parent_category_id = fields.Char(string="Tiktok Parent ID", readonly=True)
    parent_id = fields.Many2one('mp.tiktok.product.category', 'Tiktok Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    has_children = fields.Boolean(default=False)
    child_id = fields.One2many('mp.tiktok.product.category', 'parent_id', 'Tiktok Child Categories')
    permission_statuses = fields.Char(string="Tiktok Permission Status", readonly=True)
    attribute_mapped = fields.Boolean("Tiktok Attribute Mapped", default=False)
    brand_mapped = fields.Boolean("Tiktok Brand Mapped", default=False)

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
        marketplace = 'tiktok'
        mp_field_mapping = {
            'mp_external_id': ('category_id', None),
            'name': ('name', None),
            'display_name': ('display_name', None),
            'category_id': ('category_id', None),
            'has_children': ('has_children', False),
            'is_leaf': ('is_leaf', False),
            'parent_category_id': ('parent_category_id', None),
        }
        def _set_category_parent(env, data):
            mp_category_obj = env['mp.tiktok.product.category']
            if data > 0:
                mp_category = mp_category_obj.search_mp_records('tiktok', data)
                if mp_category:
                    return mp_category.id
            return False

        mp_field_mapping.update({
            'parent_id': ('parent_category_id', _set_category_parent),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPProductCategory, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tts_generate_category_data(self, mp_category_raw, mp_account_id):
        category_list = []
        category_value_obj = self.env['mp.tiktok.product.category']
        category_raw = json_digger(mp_category_raw, 'categories')

        for data in category_raw:
            category_list.append({
                'category_id': data['id'],
                'name': data['local_name'],
                'display_name': data['local_name'],
                'has_children': True if 'child' in data else False,
                'parent_category_id': data['parent_id'],
                'is_leaf': data['is_leaf']
            })
            # if 'child' in data and data['child']:
            #     for child1 in data['child']:
            #         category_list.append({
            #             'category_id': int(child1['id']),
            #             'name': child1['local_name'],
            #             'display_name': child1['local_name'],
            #             'has_children': True if 'child' in child1 else False,
            #             'parent_category_id': int(data['id']),
            #         })
            #         if 'child' in child1 and child1['child']:
            #             for child2 in child1['child']:
            #                 category_list.append({
            #                     'category_id': int(child2['id']),
            #                     'name': child2['local_name'],
            #                     'display_name': child2['local_name'],
            #                     'has_children': True if 'child' in child2 else False,
            #                     'parent_category_id': int(child1['id']),
            #                 })
        return category_list

    @api.model
    def tiktok_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_category': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPProductCategory, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values

