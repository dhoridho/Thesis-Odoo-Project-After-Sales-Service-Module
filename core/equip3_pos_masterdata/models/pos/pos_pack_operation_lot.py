# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _


class PosOrderLineLot(models.Model):
    _inherit = "pos.pack.operation.lot"

    quantity = fields.Float('Quantity')
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')

