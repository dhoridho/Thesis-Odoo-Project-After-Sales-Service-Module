from odoo import api, fields, models, _
from odoo.exceptions import Warning


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        pass
