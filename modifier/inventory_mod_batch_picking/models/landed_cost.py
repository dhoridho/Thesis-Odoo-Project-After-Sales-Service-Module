from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _target_model_selection(self) :
        return [('picking', 'Transfers'),('Batch', 'Batch Picking')]

    
    target_model = fields.Selection(
        _target_model_selection, string="Apply On",
        required=True, default='picking',
        copy=False, states={'done': [('readonly', True)]})
    
    batch_picking_ids = fields.Many2many(
        comodel_name='stock.picking.batch', 
        string='Batch Picking'
        )
    

    @api.onchange('batch_picking_ids')
    def onchange_batch_picking_ids(self):
        if self.batch_picking_ids:
            picking = self.batch_picking_ids.mapped('picking_ids')
            self.picking_ids = [(6, 0, picking.ids)]

    