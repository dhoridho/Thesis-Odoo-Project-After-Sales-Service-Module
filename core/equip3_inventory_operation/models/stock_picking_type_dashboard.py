
import time
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from itertools import groupby

class StockPickingTypeDeshboard(models.Model):
    _name = 'stock.picking.type.dashboard'
    _description = "Stock Picking Type Dashboard"
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Operation Type")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    code = fields.Selection([
        ('incoming', 'Receipt'),
        ('outgoing', 'Delivery'),
        ('internal', 'Internal Transfer'),
        ('mrp_operation', 'Manufacturing')],
        'Type of Operation')
    company_id = fields.Many2one('res.company', 'Company')
    stock_picking_type_ids = fields.One2many(
        'stock.picking.type', 'stock_picking_dasboard_id', string="Stock Picking Type")
    count_picking = fields.Integer(
        string="Pickings Count", compute='_calculate_the_picking_count', store=False)
    count_picking_ready = fields.Integer(
        string="Ready Pickings Count", compute='_calculate_the_picking_count', store=False)
    count_picking_draft = fields.Integer(
        string="Draft Pickings Count", compute='_calculate_the_picking_count', store=False)
    count_picking_waiting = fields.Integer(
        string="Waiting Pickings Count", compute='_calculate_the_picking_count', store=False)
    count_picking_late = fields.Integer(
        string="Late Pickings Count", compute='_calculate_the_picking_count', store=False)
    count_picking_backorders = fields.Integer(
        string="Backorders Pickings Count", compute='_calculate_the_picking_count', store=False)
    color = fields.Integer('Color')
    is_manufacturing = fields.Boolean(
        string="Manufacturing", compute="_compute_is_manufacturing", store=False)

    def _compute_is_manufacturing(self):
        manufacturing = self.env['ir.config_parameter'].sudo(
        ).get_param('manufacturing', False)
        for record in self:
            record.is_manufacturing = manufacturing

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        user = self.env.user
        domain = domain or []
        domain.extend(
            [('warehouse_id.company_id', 'in', user.company_ids.ids)])
        return super(StockPickingTypeDeshboard, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        user = self.env.user
        domain = domain or []
        domain.extend(
            [('warehouse_id.company_id', 'in', user.company_ids.ids)])
        return super(StockPickingTypeDeshboard, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                                 orderby=orderby, lazy=lazy)

    def _calculate_the_picking_count(self):
        for record in self:
            picking_ids = record.stock_picking_type_ids.mapped('picking_ids')
            record.count_picking = len(picking_ids)
            record.count_picking_late = len(picking_ids.filtered(lambda r: r.state in ('assigned', 'waiting', 'confirmed') and r.scheduled_date.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) < time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
            record.count_picking_ready = len(
                picking_ids.filtered(lambda r: r.state == 'assigned'))
            record.count_picking_draft = len(
                picking_ids.filtered(lambda r: r.state == 'draft'))
            record.count_picking_waiting = len(picking_ids.filtered(
                lambda r: r.state in ('confirmed', 'waiting')))
            record.count_picking_backorders = len(picking_ids.filtered(
                lambda r: r.state in ('confirmed', 'assigned', 'waiting') and r.backorder_id))

    def get_action_picking_tree_ready(self):
        return {
            'name': 'Inventory Overview',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.stock_picking_type_ids.mapped('picking_ids').filtered(lambda r:r.state == 'assigned').ids)]
        }

    def get_action_picking_tree_waiting(self):
        return {
            'name': 'Inventory Overview',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.stock_picking_type_ids.mapped('picking_ids').filtered(lambda r:r.state in ('confirmed', 'waiting')).ids)]
        }

    def get_action_picking_tree_late(self):
        return {
            'name': 'Inventory Overview',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.stock_picking_type_ids.mapped('picking_ids').filtered(lambda r:r.state in ('assigned', 'waiting', 'confirmed') and r.scheduled_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT) < time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)).ids)]
        }

    def get_action_picking_tree_backorder(self):
        return {
            'name': 'Inventory Overview',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('id', 'in', self.stock_picking_type_ids.mapped('picking_ids').filtered(lambda r:r.state in ('confirmed', 'assigned', 'waiting') and r.backorder_id).ids)]
        }
