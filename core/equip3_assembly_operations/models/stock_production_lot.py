import json
from odoo import api, fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    assembly_production_finished_id = fields.Many2one(comodel_name='assembly.production.record', string='Assembly Production Finished')
    assembly_production_byproduct_id = fields.Many2one(comodel_name='assembly.production.record', string='Assembly Production ByProduct')
    assembly_production_rejected_id = fields.Many2one(comodel_name='assembly.production.record', string='Assembly Production Rejected')

    assembly_expiration_date = fields.Datetime(string='Assembly Expiration Date')
    assembly_qty = fields.Float(string='Assmble Quantity')
    assembly_is_autogenerate = fields.Boolean(compute='_compute_assembly_is_autogenerate')
    assembly_product_tracking = fields.Selection(related='product_id.tracking', string='Assembly Tracking')

    @api.depends('product_id')
    def _compute_assembly_is_autogenerate(self):
        for record in self:
            product_id = record.product_id
            record.assembly_is_autogenerate = product_id._assembly_is_auto_generate() if product_id else False

    @api.onchange('product_id')
    def _onchange_assembly_product_tracking(self):
        if not self.product_id:
            return

        if self.product_id.tracking == 'serial':
            self.assembly_qty = 1.0
            return

        elif self.product_id.tracking == 'lot':
            context = self.env.context
            assembly_byproduct_qty = context.get('assembly_byproduct_qty', False)
            if assembly_byproduct_qty:
                assembly_byproduct_qty = json.loads(assembly_byproduct_qty)
                self.assembly_qty = assembly_byproduct_qty.get(str(self.product_id.id), 0.0)
