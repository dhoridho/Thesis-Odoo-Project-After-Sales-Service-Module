from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    gravio_record_ids = fields.Many2many('mrp.gravio.record', string='Gravio Records')
