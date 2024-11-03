# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.template"

    subscription_product = fields.Boolean(
        string='Can be Subscription/Warranty Product',
        copy=True,
    )
    recurring_rule_type = fields.Selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)'), ],
        string='Recurring Period',
        copy=True,
    )
    recurring_interval = fields.Integer(
        string="Repeat Every",
        copy=True,
    )
