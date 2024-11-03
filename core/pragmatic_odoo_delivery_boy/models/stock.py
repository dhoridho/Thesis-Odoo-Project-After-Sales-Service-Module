from odoo import api, models, fields, _


class stock_warehouse_driver(models.Model):
    _inherit = "stock.warehouse.driver"

    driver_id = fields.Many2one('res.partner', string="Delivery Boy", domain="[('is_driver', '=', True)]")

    def write(self,vals):
        res = super(stock_warehouse_driver, self).write(vals)
        if vals.get('status'):
            self.driver_id.update({
                'status': vals.get('status')
            })
        return res

    @api.model
    def create(self, vals):
        res=super(stock_warehouse_driver,self).create(vals)
        if vals.get('status'):
            partner = self.env['res.partner'].browse(int(vals.get('driver_id')))
            if partner:
                partner.status = vals.get('status')
        return res


# class StockPicking(models.Model):
#     _inherit = "stock.picking"
#
#
#     def write(self, vals):
#         if 'date_done' in vals:
#             if vals.get('date_done'):
#                 order_stage_id = self.env['order.stage'].search([('action_type', '=', 'done')])
#                 if order_stage_id:
#                     vals['stage_id'] = order_stage_id.id
#
#         if 'carrier_id' in vals and 'carrier_price' in vals:
#             order_stage_id = self.env['order.stage'].search([('action_type', '=', 'return')])
#             if order_stage_id:
#                 vals['stage_id'] = order_stage_id.id
#
#
#         return super(StockPicking, self).write(vals)


# class ReturnPicking(models.TransientModel):
#     _inherit = 'stock.return.picking'
#
#
#     def create_returns(self):
#
#
#         for wizard in self:
#             new_picking_id, pick_type_id = wizard._create_returns()
#         # Override the context to disable all the potential filters that could have been set previously
#         ctx = dict(self.env.context)
#         ctx.update({
#             'search_default_picking_type_id': pick_type_id,
#             'search_default_draft': False,
#             'search_default_assigned': False,
#             'search_default_confirmed': False,
#             'search_default_ready': False,
#             'search_default_late': False,
#             'search_default_available': False,
#         })
#         return {
#             'name': _('Returned Picking'),
#             'view_mode': 'form,tree,calendar',
#             'res_model': 'stock.picking',
#             'res_id': new_picking_id,
#             'type': 'ir.actions.act_window',
#             'context': ctx,
#         }
