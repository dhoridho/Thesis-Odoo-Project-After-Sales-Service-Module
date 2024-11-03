import json
from odoo import api, fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    kitchen_production_finished_id = fields.Many2one(comodel_name='kitchen.production.record', string='Kitchen Finished Production')
    kitchen_production_byproduct_id = fields.Many2one(comodel_name='kitchen.production.record', string='Kitchen Byproduct Production')
    kitchen_production_rejected_id = fields.Many2one(comodel_name='kitchen.production.record', string='Kitchen Rejected Production')

    kitchen_expiration_date = fields.Datetime(string='Kitchen Expiration Date')
    kitchen_qty = fields.Float(string='Kitchen Quantity')
    kitchen_is_autogenerate = fields.Boolean(compute='_compute_kitchen_is_autogenerate')
    kitchen_product_tracking = fields.Selection(related='product_id.tracking', string='Kitchen Tracking')

    @api.depends('product_id')
    def _compute_kitchen_is_autogenerate(self):
        for record in self:
            product_id = record.product_id
            record.kitchen_is_autogenerate = product_id._kitchen_is_auto_generate() if product_id else False

    @api.onchange('product_id')
    def _onchange_kitchen_product_tracking(self):
        if not self.product_id:
            return

        if self.product_id.tracking == 'serial':
            self.kitchen_qty = 1.0
            return

        elif self.product_id.tracking == 'lot':
            context = self.env.context
            kitchen_byproduct_qty = context.get('kitchen_byproduct_qty', False)
            if kitchen_byproduct_qty:
                kitchen_byproduct_qty = json.loads(kitchen_byproduct_qty)
                self.kitchen_qty = kitchen_byproduct_qty.get(str(self.product_id.id), 0.0)
