
from odoo import api , fields , models
from datetime import datetime, date


class AccountAssetAssets(models.Model):
    _inherit = "account.asset.asset"
 
    serial_number_id = fields.Many2one('stock.production.lot')