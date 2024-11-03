from odoo import tools, models, fields, api, _ 
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inv_line_ids = fields.Many2many('account.move', string="Invoice Reference", readonly=True)

    def action_view_stock_valuation_layers(self):
        action = super(StockPicking, self).action_view_stock_valuation_layers()
        domain = expression.OR([
            action.get('domain', []), 
            [('stock_valuation_layer_id', 'in', self.move_lines.stock_valuation_layer_ids.ids)]
        ])
        return dict(action, domain=domain)
