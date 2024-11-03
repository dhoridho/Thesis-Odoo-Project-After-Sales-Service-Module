# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    _description = 'Product Attribute'

    is_marketplace = fields.Boolean(string="is Marketplace?", default=False)
    variant_id = fields.Integer(string='Variant ID', readonly=True)
    has_unit = fields.Integer(string='Has Unit', readonly=True)
    identifier = fields.Char(string='Identifier')
    status = fields.Integer(string='Status')
    is_primary = fields.Integer(string='Is Primary')
    variant_unit_ids = fields.One2many('product.attribute.unit', 'attribute_id', string='Product Attribute Unit', readonly=True, ondelete="cascade")


class ProductAttributeVariantUnit(models.Model):
    _name = 'product.attribute.unit'
    _description = 'Product Attribute Variant Unit'

    name = fields.Char(string='Unit Name')
    short_name = fields.Char(string='Short Name')
    unit_id = fields.Integer(string='Variant ID', readonly=True)
    status = fields.Integer(string='Unit Status')
    attribute_id = fields.Many2one(comodel_name='product.attribute', string='Product Attribute', readonly=True)
    attribute_value_id = fields.One2many('product.attribute.value', 'attribute_unit_id', string='Product Attribute Value', readonly=True)


class ProductAttributeVariantValue(models.Model):
    _inherit = 'product.attribute.value'
    _description = 'Product Attribute Variant Value'

    english_name = fields.Char(string='English Name')
    unit_value_id = fields.Integer(string='Variant Unit Value ID', readonly=True)
    status = fields.Integer(string='Value Status')
    attribute_unit_id = fields.Many2one(comodel_name='product.attribute.unit', string='Attribute Unit', readonly=True)
    hex = fields.Char(string='Hex')
    icon = fields.Char(string='Icon')


class ProductAttributeMarketplaceValue(models.Model):
    _name = 'product.attribute.marketplace.value'
    _description = "Product Attribute Marketplace Value"

    product_tmpl_id = fields.Many2one('product.template', string='Template')
    product_id = fields.Many2one('product.product', string='Product')
    attribute_id = fields.Many2one('product.attribute', string="Attribute")
    attribute_value_ids = fields.Many2many('product.template.attribute.value',
                'product_attribute_marketplace_value_rel',
                string='Attribute Values')
    default_code = fields.Char("Default Code")
    quantity = fields.Integer("Qty", default=1)
    sales_price = fields.Float("Sales Price", default=100.0)


    def write(self, values):
        res = super(ProductAttributeMarketplaceValue, self).write(values)
        product = self.env['product.product'].search([('id', '=', self.product_id.id)])
        if 'default_code' in values:
            product.default_code = self.default_code
        if 'quantity' in values:
            product.normal_stock = self.quantity
        if 'sales_price' in values:
            product.variant_price = self.sales_price

