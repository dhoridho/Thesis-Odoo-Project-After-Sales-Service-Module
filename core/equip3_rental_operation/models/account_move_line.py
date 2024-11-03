
from odoo import api , fields , models
from datetime import datetime, date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
 
    serial_number_id = fields.Many2one('stock.production.lot')
    