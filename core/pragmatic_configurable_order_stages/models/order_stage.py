# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class OrderStage(models.Model):
    _name = "order.stage"
    _description = "Order stages"
    _order = "sequence, id"

    @api.model
    def _default_warehouse_ids(self):
        company_id = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company_id)])
        return warehouse_ids

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    warehouse_ids = fields.Many2many('stock.warehouse', 'order_stage_warehouse_rel', 'stage_id', 'warehouse_id',
                                     string='Warehouses', default=_default_warehouse_ids)
    action_type = fields.Selection([
        ('draft', 'draft'),
        ('sent', 'sent'),
        ('sale', 'sale'),
        ('progress', 'progress'),
        ('ready', 'ready'),
        ('assigned', 'assigned'),
        ('picked', 'picked'),
        ('payment', 'payment'),
        ('delivered', 'delivered'),
        ('done', 'done'),
        ('cancel', 'cancel'),
        ('return', 'return')], string='Action Type',
        help="Hard coded action type for order stages, to drive order progress "
                              "through web interface")
    is_hidden = fields.Boolean(string="Hidden", default=False)
    planned_date = fields.Datetime(string="Planned Date")
    actual_date = fields.Datetime(string="Actual Date")

    @api.model
    def get_order_stages(self, warehouse_id):
        order_stages = self.env['order.stage'].search([('warehouse_ids', '=', warehouse_id),('is_hidden','=',False)], order="sequence, id")
        return order_stages


class SaleOrder(models.Model):
    _inherit = "sale.order"

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

        return super(SaleOrder, self.with_context(context)).create(vals)