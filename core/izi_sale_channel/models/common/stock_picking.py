from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    sale_channel_id = fields.Many2one(comodel_name='sale.channel', string="Sales Channel")
