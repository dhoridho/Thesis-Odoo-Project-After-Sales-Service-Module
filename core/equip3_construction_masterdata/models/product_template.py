# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    control_purchase_bill = fields.Selection([
        ('on_order_qty', 'On Order Quantity'),
        ('on_received_qty', 'On Received Quantity'),
    ], string='Control Purchase Bill', default='on_received_qty')
    is_work_order = fields.Boolean(string="Is Work Order")
    investment = fields.Boolean(string="Investment")
    service_category = fields.Selection([('labour', 'Labour')], string='Service Category')
    group_of_product = fields.Many2many('group.of.product', 'product_gop_rel', 'product_template_id', 'gop_id', string='Group of Product')
    labour_type = fields.Boolean(string='Is Labour', default=False)

    