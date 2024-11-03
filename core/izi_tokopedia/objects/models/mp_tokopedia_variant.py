# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.addons.izi_marketplace.objects.utils.tools import json_digger

class MPTokopediaVariant(models.Model):
    _name = 'mp.tokopedia.variant'
    _description = 'Marketplace Tokopedia Variant'

    name = fields.Char(string="Product Variant Name", readonly=True)
    variant_id = fields.Integer(string='Variant ID', readonly=True)
    has_unit = fields.Integer(string='Has Unit', readonly=True)
    identifier = fields.Char(string='Identifier')
    status = fields.Integer(string='Status')
    is_primary = fields.Integer(string='Is Primary')
    variant_unit_ids = fields.One2many('mp.tokopedia.variant.unit', 'variant_id', string='Product Variant Unit', readonly=True, ondelete="cascade")
    tp_category_id = fields.Many2one('mp.tokopedia.category', string="Category", required=False)


    ### penambahan function baru
    @api.model
    def tp_generate_variant_data(self, mp_product_raw):
        variant_list = []

        varian_model = json_digger(mp_product_raw, 'variant_details')
        varian_tier = json_digger(mp_product_raw, 'variant_id_combinations')

        tp_category_id = self._set_category_variant(json_digger(mp_product_raw, 'category_id'))

        attrib_line = self.set_product_variant(tp_category_id, varian_model)

        for model in varian_model:
            variant_dict = {
                'category_id': json_digger(mp_product_raw, 'category_id'),
                'tp_variant_id': json_digger(model, 'variant_id'),
                'variant_line': attrib_line,
            }
            variant_list.append(variant_dict)

        return variant_list


    def _set_category_variant(self, category_id):
        mp_category_obj = self.env['mp.tokopedia.category']
        mp_category = mp_category_obj.search_mp_records('tokopedia', category_id)
        if mp_category:
            return mp_category.id
        return False

    def set_product_variant(self, category_id, tier_variation):
        attribute = False
        attribute_line = []
        attribute_unit_line = []
        attribute_value_line = []
        if tier_variation:
            val_name = False
            for res in tier_variation:
                attrib = self.env['mp.tokopedia.variant'].sudo().search([('name', '=', res.get("name")), ('variant_id', '=', res.get("variant_id")), ('tp_category_id', '=', category_id)])
                if not attrib:
                    attribute = self.env['mp.tokopedia.variant'].sudo().create({
                        'name': res.get("name"),
                        'variant_id': res.get("variant_id"),
                        'has_unit': res.get("has_unit"),
                        'identifier': res.get("identifier"),
                        'status': res.get("status"),
                        'is_primary': res.get("is_primary"),
                        'tp_category_id': category_id
                    }).id
                else:
                    attribute = attrib.id
                attribute_unit_ids = []
                if res.get("units"):
                    for unit in res.get("units"):
                        att_unit_id = False
                        if unit.get("variant_unit_id") > 0:
                            unit_name = unit.get('unit_name')
                            att_unit = self.env['mp.tokopedia.variant.unit'].sudo().search(
                                [('name', '=', unit_name), ('unit_id', '=', unit.get("variant_unit_id")), ('variant_id', '=', attribute)])
                            if att_unit:
                                # attribute_val_ids.append((6, 0, att_val.ids))
                                attribute_unit_ids.append(int(att_unit.id))
                                att_unit_id = att_unit.id
                            else:
                                att_unit_id = self.env['mp.tokopedia.variant.unit'].sudo().create({
                                    'name': unit_name,
                                    'short_name': unit.get("unit_short_name"),
                                    'status': unit.get("status"),
                                    'unit_id': unit.get("variant_unit_id"),
                                    'variant_id': int(attribute)
                                }).id
                                attribute_unit_ids.append(int(att_unit_id))
                        attribute_val_ids = []
                        if unit.get("unit_values"):
                            for line in unit.get("unit_values"):
                                val_name = line.get('value')
                                att_val = self.env['mp.tokopedia.variant.value'].sudo().search(
                                    [('name', '=', val_name), ('unit_value_id', '=', line.get("variant_unit_value_id")), ('variant_id', '=', attribute)])
                                if att_val:
                                    # attribute_val_ids.append((6, 0, att_val.ids))
                                    attribute_val_ids.append(int(att_val.id))
                                    att_val_id = att_val.id
                                else:
                                    att_val_id = self.env['mp.tokopedia.variant.value'].sudo().create({
                                        'name': val_name,
                                        'short_name': val_name,
                                        'equivalent_value_id': line.get("equivalent_value_id"),
                                        'english_name': line.get("english_value"),
                                        'unit_value_id': line.get("variant_unit_value_id"),
                                        'status': line.get("status"),
                                        'hex': line.get("hex"),
                                        'icon': line.get("icon"),
                                        'variant_unit_id': att_unit_id,
                                        'variant_id': int(attribute)
                                    }).id
                                    attribute_val_ids.append(int(att_val_id))
                                attribute_value_line.append({
                                    'value_id': attribute_val_ids
                                })
                        attribute_unit_line.append({
                            'unit_id': attribute_unit_ids,
                            'variant_value_id': attribute_value_line
                        })
                attribute_line.append({
                    'variant_id': int(attribute),
                    'variant_unit_id': attribute_unit_line
                })
                # self.env['product.attribute'].sudo().write({'value_ids': attribute_val_ids})
        return attribute_line

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='response')
        return {
            'get_attributes': default_sanitizer
        }

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(MPTokopediaVariant, self)._finish_mapping_raw_data(sanitized_data, values)
        return sanitized_data, values


class MPTokopediaAttributeUnit(models.Model):
    _name = 'mp.tokopedia.variant.unit'
    _description = 'Marketplace Tokopedia Variant Unit'

    name = fields.Char(string='Unit Name')
    short_name = fields.Char(string='Short Name')
    unit_id = fields.Integer(string='Variant Unit ID', readonly=True)
    status = fields.Integer(string='Unit Status')
    variant_id = fields.Many2one(comodel_name='mp.tokopedia.variant', string='Product Variant', readonly=True)
    variant_value_ids = fields.One2many('mp.tokopedia.variant.value', 'variant_unit_id', string='Product Variant Value', readonly=True)


class MPTokopediaAttributeValue(models.Model):
    _name = 'mp.tokopedia.variant.value'
    _description = 'Marketplace Tokopedia Variant Value'

    name = fields.Char(string="Product Variant Value Name", readonly=True)
    short_name = fields.Char(string="Product Variant Short Name", readonly=True)
    english_name = fields.Char(string='English Name')
    unit_value_id = fields.Integer(string='Variant Unit Value ID', readonly=True)
    equivalent_value_id = fields.Integer(string='Equivalent Value ID', readonly=True)
    status = fields.Integer(string='Value Status')
    variant_unit_id = fields.Many2one(comodel_name='mp.tokopedia.variant.unit', string='Variant Unit', readonly=True)
    hex = fields.Char(string='Hex')
    icon = fields.Char(string='Icon')
    variant_id = fields.Many2one('mp.tokopedia.variant', string='Attribute ID')


