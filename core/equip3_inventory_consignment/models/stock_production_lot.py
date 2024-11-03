from odoo import _, api, fields, models
from datetime import datetime, date, timedelta

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    is_consignment = fields.Boolean()
    consignment_agreement = fields.Many2one('consignment.agreement')
