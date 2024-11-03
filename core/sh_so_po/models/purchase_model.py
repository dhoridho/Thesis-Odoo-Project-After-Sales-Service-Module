# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sh_sale_order_id = fields.Many2one(
        "sale.order", string="Sale Order", readonly=True)
