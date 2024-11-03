# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    is_depreciation_asset_created = fields.Boolean('Depreciation Asset Created', default=False)
    is_asset_control_created = fields.Boolean('Asset Control Created', default=False)