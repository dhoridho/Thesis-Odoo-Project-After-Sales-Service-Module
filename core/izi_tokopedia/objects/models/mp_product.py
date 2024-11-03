# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class MarketplaceProduct(models.Model):
    _inherit = 'mp.product'

    tp_product_id = fields.Char(string='Tokopedia Product ID', readonly=True)
    tp_has_variant = fields.Boolean(string='Tokopedia Product has Variant', readonly=True)
    tp_item_status = fields.Selection([
        ('-2', 'Banned'),
        ('-1', 'Pending'),
        ('0', 'Deleted'),
        ('1', 'Active'),
        ('2', 'Best (Feature Product)'),
        ('3', 'Inactive (Warehouse)'),
    ], string='Product Status', default='1')
    tp_stock_status = fields.Selection([
        ('LIMITED', 'LIMITED'),
        ('EMPTY', 'EMPTY'),
        ('UNLIMITED', 'UNLIMITED'),
    ], string='Stock Status', default='LIMITED')
    tp_category_id = fields.Many2one('mp.tokopedia.category', string='Category', required=False)
    tp_child_category_id = fields.Integer('Category ID')
    tp_attribute_ids = fields.One2many('mp.tokopedia.attribute.line', 'tp_product_id', string='Attribute', ondelete='cascade')
    tp_variant_line = fields.Text('Attribute Line')
    tp_condition = fields.Selection([
        ('NEW', 'New'),
        ('USED', 'Used'),
    ], string='Condition', default='NEW')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'mp_external_id': ('basic/productID', lambda env, r: str(r)),
            'tp_product_id': ('basic/productID', lambda env, r: str(r)),
            'tp_has_variant': ('variant/isParent', lambda env, r: r if r else False),
            'name': ('basic/name', None),
            'description_sale': ('basic/shortDesc', None),
            # 'default_code': ('other/sku', lambda env, r: r.strip() if r else False),
            'list_price': ('price/value', None),
            'weight': ('weight/value', None),
            'length': ('volume/length', None),
            'width': ('volume/width', None),
            'height': ('volume/height', None),
            'tp_item_status': ('basic/status', lambda env, r: str(r)),
            'tp_child_category_id': ('basic/childCategoryID', None),
        }

        def _handle_pictures(env, data):
            mp_product_image_obj = env['mp.product.image']

            mp_product_image_data = [(5,)]

            raw_datas, sanitized_datas = mp_product_image_obj._prepare_mapping_raw_data(raw_data=data)
            sanitized_datas, values_list = mp_product_image_obj._run_mapping_raw_data(raw_datas, sanitized_datas,
                                                                                      multi=isinstance(sanitized_datas,
                                                                                                       list))
            for values in values_list:
                mp_product_image_data.append((0, 0, values))

            return mp_product_image_data

        def _handle_wholesale(env, data):
            if data:
                wholesales = [(5, 0, 0)]
                for wholesale in data:
                    vals = {
                        'mp_account_id': env.context['mp_account_id'],
                        'min_qty': wholesale['minQuantity'],
                        'max_qty': wholesale['maxQuantity'],
                        'price': wholesale['price']['value'],
                    }
                    wholesales.append((0, 0, vals))
                return wholesales
            return None

        def _handle_item_status(env, data):
            if data:
                if data == 1:
                    return True
                else:
                    return False
            return False

        def _set_item_condition(env, data):
            if data:
                if int(data) == 1:
                    return 'NEW'
                else:
                    return 'USED'
            return False

        def _set_item_category(env, data):
            mp_category_obj = env['mp.tokopedia.category']
            mp_category = mp_category_obj.search_mp_records('tokopedia', data)
            if mp_category:
                return int(mp_category.id)
            return False

        def _set_default_code(env, data):
            category_obj = env['product.category'].search([('name', 'ilike', '%marketplace')], limit=1)
            current_code = None
            if category_obj:
                category_sequence = int(category_obj.current_sequence)+1
                current_code = category_obj.category_prefix + '-' + str(f"{category_sequence :03d}")
                category_obj.current_sequence = str(f"{category_sequence :03d}")
            if data:
                if data.get('sku'):
                    product_code = data.get('sku')
                else:
                    product_code = current_code
                return product_code
            return False


        mp_field_mapping.update({
            # 'default_code': ('other/sku', 'basic/productID'),
            'default_code': ('other', _set_default_code),
            'mp_product_image_ids': ('pictures', _handle_pictures),
            'mp_product_wholesale_ids': ('wholesale', _handle_wholesale),
            'is_active': ('basic/status', _handle_item_status),
            'tp_category_id': ('basic/childCategoryID', _set_item_category),
            'tp_condition': ('basic/condition', _set_item_condition),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceProduct, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def create(self, values):
        if 'marketplace' in values and values.get('marketplace') == 'tokopedia':
            if 'tp_category_id' in values and not values.get('tp_category_id'):
                raise ValidationError('Tokopedia: Category not found')
        return super(MarketplaceProduct, self).create(values)

    @api.model
    def tokopedia_get_sanitizers(self, mp_field_mapping):
        default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
        return {
            'product_info': default_sanitizer
        }

    @api.onchange('tp_category_id')
    def _onchange_set_attribute_mp_product_tokopedia(self):
        for res in self:
            if res.tp_category_id:
                attribute_line = [(5, 0)]
                attrib_line_obj = self.env['mp.tokopedia.attribute.line'].search([('category_id', '=', res.tp_category_id.id), ('tp_product_id', '=', res.id)])
                res.tp_attribute_ids = False
                if attrib_line_obj:
                    attribute_line += [(0, 0, {
                        'attribute_id': rec.attribute_id.id,
                        'attribute_value_id': rec.attribute_value_id.id,
                        'category_id': rec.category_id.id,
                        'tp_product_id': rec.tp_product_id.id
                    }) for rec in attrib_line_obj]
                    res.tp_attribute_ids = attribute_line
                else:
                    attrib_obj = self.env['mp.tokopedia.attribute'].search([('category_id', '=', res.tp_category_id.id)])
                    if attrib_obj:
                        attribute_line += [(0, 0, {
                            'attribute_id': rec.id,
                            'attribute_value_id': False,
                            'category_id': res.tp_category_id.id,
                            'tp_product_id': res.id
                        }) for rec in attrib_obj]
                        res.tp_attribute_ids = attribute_line
            else:
                res.tp_attribute_ids = False
