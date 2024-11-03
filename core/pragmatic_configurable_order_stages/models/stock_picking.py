# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools


class stock_picking(models.Model):
    _inherit = "stock.picking"

    def _default_stage(self):
        warehouse_id = self.env.context.get('default_warehouse_id')
        if not warehouse_id:
            return False
        return self.env['order.stage'].search([('warehouse_ids', '=', warehouse_id)], order="sequence", limit=1).id

    stage_id = fields.Many2one('order.stage', string='State', ondelete='restrict', tracking=True, index=True,
                               default=_default_stage, domain="[('warehouse_ids', '=', warehouse_id)]", copy=False)

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        context = dict(self.env.context)
        # for default stage
        if vals.get('warehouse_id') and not context.get('default_project_id'):
            context['default_warehouse_id'] = vals.get('warehouse_id')

        return super(stock_picking, self.with_context(context)).create(vals)

    def write(self, vals):
        if 'state' in vals:
            if vals.get('state'):
                order_stage_id = self.env['order.stage'].search([('action_type', '=', vals.get('state'))])
                if order_stage_id:
                    vals['stage_id'] = order_stage_id.id
        if 'date_done' in vals:
            if vals.get('date_done'):
                order_stage_id = self.env['order.stage'].search([('action_type', '=', 'done')])
                if order_stage_id:
                    vals['stage_id'] = order_stage_id.id

        if 'carrier_id' in vals and 'carrier_price' in vals:
            order_stage_id = self.env['order.stage'].search([('action_type', '=', 'return')])
            if order_stage_id:
                vals['stage_id'] = order_stage_id.id

        return super(stock_picking, self).write(vals)

