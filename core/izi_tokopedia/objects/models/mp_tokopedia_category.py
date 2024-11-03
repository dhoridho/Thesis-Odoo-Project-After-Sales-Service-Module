# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import json
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger

class MPTokopediaCategory(models.Model):
    _name = 'mp.tokopedia.category'
    _inherit = 'mp.base'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'display_name'
    _order = 'display_name'
    _description = 'Marketplace Tokopedia Category'

    name = fields.Char(string="Product Category Name", readonly=True)
    display_name = fields.Char(string="Category Name", compute='_compute_complete_name', store=True)
    # parent_id = fields.Integer("Parent Category ID")
    parent_id = fields.Many2one('mp.tokopedia.category', 'Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    has_children = fields.Boolean(default=False)
    child_id = fields.One2many('mp.tokopedia.category', 'parent_id', 'Child Categories')
    category_id = fields.Integer(string="Tokopedia Category ID", readonly=True)
    parent_category_id = fields.Integer(string="Tokopedia Parent Category ID", readonly=True)
    attribute_mapped = fields.Boolean("Attribute Mapped", default=False)
    variant_mapped = fields.Boolean("Variant Mapped", default=False)

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
        marketplace = 'tokopedia'
        mp_field_mapping = {
            'mp_external_id': ('category_id', None),
            'name': ('name', None),
            'display_name': ('display_name', None),
            'category_id': ('category_id', None),
            'has_children': ('has_children', False),
            'parent_category_id': ('parent_category_id', None),
        }
        def _set_category_parent(env, data):
            mp_category_obj = env['mp.tokopedia.category']
            if data > 0:
                mp_category = mp_category_obj.search_mp_records('tokopedia', data)
                if mp_category:
                    return mp_category.id
            return False

        mp_field_mapping.update({
            'parent_id': ('parent_category_id', _set_category_parent),
        })
        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPTokopediaCategory, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def tp_generate_category_data(self, mp_category_raw, mp_account_id):
        category_list = []
        category_value_obj = self.env['mp.tokopedia.category']
        category_raw = json_digger(mp_category_raw, 'categories')

        for data in category_raw:
            category_list.append({
                'category_id': int(data['id']),
                'name': data['name'],
                'display_name': data['name'],
                'has_children': True if 'child' in data else False,
                'parent_category_id': 0,
            })
            if 'child' in data and data['child']:
                for child1 in data['child']:
                    category_list.append({
                        'category_id': int(child1['id']),
                        'name': child1['name'],
                        'display_name': child1['name'],
                        'has_children': True if 'child' in child1 else False,
                        'parent_category_id': int(data['id']),
                    })
                    if 'child' in child1 and child1['child']:
                        for child2 in child1['child']:
                            category_list.append({
                                'category_id': int(child2['id']),
                                'name': child2['name'],
                                'display_name': child2['name'],
                                'has_children': True if 'child' in child2 else False,
                                'parent_category_id': int(child1['id']),
                            })
        return category_list

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_category': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPTokopediaCategory, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values

