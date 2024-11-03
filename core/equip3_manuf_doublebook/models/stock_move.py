from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = ['stock.move', 'base.synchro.abstract']

    def sync_unlink(self):
        moves = self.filtered(lambda o: o.base_sync)
        moves.unlink()
