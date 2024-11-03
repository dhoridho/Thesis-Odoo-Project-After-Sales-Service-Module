import json
from odoo import models, fields, api


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.depends('product_id')
    def _compute_is_autogenerate(self):
        for record in self:
            product_id = record.product_id
            record.is_autogenerate = product_id._is_auto_generate() if product_id else False

    consumption_finished_id = fields.Many2one('mrp.consumption', string='Finished Production Record')
    consumption_rejected_id = fields.Many2one('mrp.consumption', string='Rejected Production Record')
    consumption_byproduct_id = fields.Many2one('mrp.consumption', string='ByProduct Production Record')

    mrp_consumption_expiration_date = fields.Datetime(string='MRP Consumption Expiration Date')
    consumption_qty = fields.Float(string='Consumption Quantity')
    product_tracking = fields.Selection(related='product_id.tracking')
    is_autogenerate = fields.Boolean(compute=_compute_is_autogenerate)

    @api.model
    def create(self, vals):
        rec = super(StockProductionLot, self).create(vals)
        if self.env.context.get('force_blank_expiration_date'):
            rec.expiration_date = False
        return rec

    @api.onchange('product_id')
    def _onchange_product_tracking(self):
        if not self.product_id:
            return

        if self.product_id.tracking == 'serial':
            self.consumption_qty = 1.0
            return

        elif self.product_id.tracking == 'lot':
            context = self.env.context
            context_qty = context.get('mpr_byproduct_qty', False) or context.get('mpr_finished_qty', False)
            if context_qty:
                context_qty = json.loads(context_qty)
                self.consumption_qty = context_qty.get(str(self.product_id.id), 0.0)
