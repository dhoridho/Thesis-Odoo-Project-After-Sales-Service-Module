# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CateringSubscription(models.Model):
    _name = 'catering.subscription'
    _rec_name = 'duration'

    duration = fields.Integer("Duration (Days)")
    price = fields.Integer("Price")
    product_id = fields.Many2one('product.template')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_catering = fields.Boolean("Is Catering Product")
    is_catering_product = fields.Boolean("Is Catering Product")
    catering_type = fields.Selection([
        ('package', 'Package'),
        ('menu', 'Menu'),
    ], 'Product Type', tracking=True, required=True)

    subscription = fields.One2many('catering.subscription', 'product_id', string='Subscription', tracking=True)
    monday = fields.Boolean("Monday", tracking=True)
    tuesday = fields.Boolean("Tuesday", tracking=True)
    wednesday = fields.Boolean("Wednesday", tracking=True)
    thursday = fields.Boolean("Thursday", tracking=True)
    friday = fields.Boolean("Friday", tracking=True)
    saturday = fields.Boolean("Saturday", tracking=True)
    sunday = fields.Boolean("Sunday", tracking=True)
    meal_type_id = fields.Many2one('meals.type', "Meal Type", tracking=True)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_catering = fields.Boolean("Is Catering Product", related='product_tmpl_id.is_catering')
    catering_type = fields.Selection([
        ('package', 'Package'),
        ('menu', 'Menu'),
    ], 'Product Type', related='product_tmpl_id.catering_type')