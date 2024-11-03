# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"

    product_template_id = fields.Many2one(
        "product.template", string="Product", readonly=True
    )
    serial_number_id = fields.Many2one("stock.production.lot")


class AccountMoveLineInherit(models.Model):
    _inherit = "account.move.line"

    serial_number_id = fields.Many2one("stock.production.lot")
