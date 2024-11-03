from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from datetime import datetime
import datetime


class StockDayAverage(models.Model):
    _name = 'stock.day.average'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Stock Day Average'

    name = fields.Char(string='Name', default='New', tracking=True)
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product', tracking=True)
    action_type = fields.Selection(string='Action To Take', selection=[
                                   ('transfer', 'Internal Transfer')], tracking=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', tracking=True, default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=True, default=lambda self: self.env.company)
    users_ids = fields.Many2many(
        comodel_name='res.users', string='Responsible', tracking=True)
    start_date = fields.Date(string='Run Rate Start Date', tracking=True)
    end_date = fields.Date(string='Run Rate End Date', tracking=True)
    periode = fields.Integer(string='Calculation Period', tracking=True)
    cluster_id = fields.Many2one(
        comodel_name='cluster.area', string='Cluster', tracking=True)
    is_itr_created = fields.Boolean(
        string='Is Internal Transfer Created', default=False)
    transfer_count = fields.Integer(
        string='Transfer Count', compute='compute_transfer_count')
    warehouse_line = fields.One2many(
        comodel_name='stock.day.average.line', inverse_name='order_id', string='Warehouse')
    is_computed = fields.Boolean(string='Computed', default=False)
    percent_for_avl = fields.Float(
        'Percent for Available Quantity', default=20)

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'stock.day.average') or _('New')
        result = super(StockDayAverage, self).create(vals)
        return result

    def compute_transfer_count(self):
        for rec in self:
            rec.transfer_count = self.env['internal.transfer'].search_count(
                [('average_id', '=', rec.id)])

    @api.onchange('start_date')
    def onchange_start_date(self):
        if self.start_date:
            self.end_date = self.start_date + relativedelta(years=1)
            self.periode = (self.end_date - self.start_date).days

    @api.onchange('end_date')
    def onhcange_end_date(self):
        if self.end_date:
            self.periode = (self.end_date - self.start_date).days

    @api.onchange('cluster_id')
    def onchange_cluster_id(self):
        total_quantity = 0
        total_run_rate = 0
        total_average_stock = 0
        if self.cluster_id and self.product_id:
            self.warehouse_line = [(5, 0, 0)]
            warehouse_ids = self.cluster_id.warehouse_line.mapped(
                'warehouse_id')
            location_ids = self.env['stock.location'].search(
                [('warehouse_id', 'in', warehouse_ids.mapped('id'))])
            stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', self.product_id.id), ('location_id', 'in', location_ids.ids)])
            self.warehouse_line = False
            for warehouse in self.cluster_id.warehouse_line:
                self.warehouse_line = [(0, 0, {
                    'warehouse_id': warehouse.warehouse_id.id,
                    'quantity': sum(stock_quant.filtered(lambda x: x.location_id.id in location_ids.filtered(lambda y: y.warehouse_id.id == warehouse.warehouse_id.id).ids).mapped('available_quantity')),
                    # 'quantity': sum(stock_quant.filtered(lambda x: x.location_id.id == warehouse.warehouse_id.lot_stock_id.id).mapped('available_quantity')), #per location
                })]

    def action_compute(self):
        total_quantity = 0
        total_run_rate = 0
        total_average_stock = 0
        for rec in self.warehouse_line:
            warehouse_id = self.warehouse_line.mapped('warehouse_id')
            picking = self.env['stock.picking'].search([('picking_type_code', '=', 'outgoing'), (
                'state', '=', 'done'), ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)])
            location_ids = self.env['stock.location'].search(
                [('warehouse_id', 'in', warehouse_id.mapped('id'))])
            stock_quant = self.env['stock.quant'].search(
                [('product_id', '=', self.product_id.id), ('location_id', 'in', location_ids.ids)])
            count = 0
            for pick in picking:
                products = [
                    rec.product_id.id for rec in pick.move_ids_without_package]
                if rec.warehouse_id.id == pick.picking_type_id.warehouse_id.id and self.product_id.id in products:
                    count += sum(pick.move_ids_without_package.mapped('quantity_done'))
                    rec.run_rate = round(count / self.periode, 2)

            rec.quantity = sum(stock_quant.filtered(lambda x: x.location_id.id in location_ids.filtered(
                lambda y: y.warehouse_id.id == rec.warehouse_id.id).ids).mapped('available_quantity'))
            # rec.quantity = sum(stock_quant.filtered(lambda x: x.location_id.id == rec.warehouse_id.lot_stock_id.id).mapped('available_quantity')) #per location
            if rec.run_rate > 0 and rec.quantity > 0:
                rec.stock_days = rec.quantity / rec.run_rate

            total_quantity += rec.quantity
            total_run_rate += rec.run_rate
            if total_quantity > 0 and total_run_rate > 0:
                total_average_stock = total_quantity / total_run_rate

        for x in self.warehouse_line:
            x.average_stock = total_average_stock if x.run_rate > 0 else 0
            x.optimal_qty = total_average_stock * x.run_rate
            x.total_optimal_qty = round(x.optimal_qty - x.quantity)
        self.is_computed = True

    def _prepare_itr_values(self, wh_source, loc_source, wh_dest, loc_dest, qty):
        self.is_itr_created = True
        today = datetime.datetime.today()
        vals = {
            'average_id': self.id,
            'requested_by': self.env.user.id,
            'source_warehouse_id': wh_source,
            'source_location_id': loc_source,
            'destination_warehouse_id': wh_dest,
            'destination_location_id': loc_dest,
            'scheduled_date': today,
            'branch_id': self.branch_id.id,
            'product_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'description': self.product_id.name,
                'uom': self.product_id.uom_id.id,
                'qty': qty,
                'scheduled_date': today,
                'source_location_id': loc_source,
                'destination_location_id': loc_dest
            })],
        }
        itr = self.env['internal.transfer'].create(vals)
        itr.onchange_dest_loction_id()
        itr.onchange_source_loction_id()

    def action_create_itr(self):
        not_need = self.warehouse_line.sorted(
            key=lambda x: x.total_optimal_qty).filtered(lambda x: not x.is_need_itr)
        need = self.warehouse_line.sorted(
            key=lambda x: x.total_optimal_qty, reverse=True).filtered(lambda x: x.is_need_itr)

        for x in not_need:
            kelebihan = abs(x.total_optimal_qty)
            qty = 0

            for y in need:
                kekurangan = y.total_optimal_qty
                qty = kekurangan if kekurangan < kelebihan else kelebihan

                if kelebihan > 0 and qty > 0:
                    # print('KONDISI 2 > DARI', x.warehouse_id.name, 'KE', y.warehouse_id.name, 'SEBANYAK', qty, '| KEKURANGAN', kekurangan, '| KELEBIHAN', kelebihan)
                    self._prepare_itr_values(x.warehouse_id.id, x.warehouse_id.lot_stock_id.id,
                                             y.warehouse_id.id, y.warehouse_id.lot_stock_id.id, qty)
                    kelebihan -= qty
                    y.total_optimal_qty -= qty
                    if kelebihan == 0:
                        # print('KONDISI 1 > DARI', x.warehouse_id.name, 'KE', y.warehouse_id.name, 'SEBANYAK', qty, '| KEKURANGAN', kekurangan, '| KELEBIHAN', kelebihan)
                        break


    def action_view_itr(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfer'),
            'res_model': 'internal.transfer',
            'view_mode': 'tree,form',
            'domain': [('average_id', '=', self.id)],
        }


class StockDayAverageLine(models.Model):
    _name = 'stock.day.average.line'
    _description = 'Stock Day Average Line'

    order_id = fields.Many2one(
        comodel_name='stock.day.average', string='Order')
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse')
    quantity = fields.Float(string='Available Quantity')
    run_rate = fields.Float(string='Run Rate')
    stock_days = fields.Float(string='Stock Days')
    average_stock = fields.Float(string='Average Stock Days')
    optimal_qty = fields.Float(string='Optimal Quantity')
    total_optimal_qty = fields.Float(string='Total Optimal Quantity')
    is_need_itr = fields.Boolean(string='Need ITR', compute='compute_need_itr')
    risk_assesment = fields.Char(
        'Risk Assesment', compute='_compute_risk_assesment')

    def compute_need_itr(self):
        for rec in self:
            rec.is_need_itr = False
            if rec.optimal_qty > rec.quantity:
                rec.is_need_itr = True
            else:
                rec.is_need_itr = False

    def _compute_risk_assesment(self):
        for stock in self.order_id:
            if stock.percent_for_avl:
                percent = stock.percent_for_avl
            else:
                percent = 20
        for rec in self:
            if percent:
                rec_higher = rec.quantity + (rec.quantity * percent/100)
                rec_lower = rec.quantity - (rec.quantity * percent/100)

                if rec.optimal_qty < rec_lower:
                    rec.risk_assesment = 'Overstock'
                elif rec_lower <= rec.optimal_qty <= rec_higher:
                    rec.risk_assesment = 'Healthy'

                else:
                    rec.risk_assesment = 'Understock'


# class InternalTransferInherit(models.Model):
#     _inherit = 'internal.transfer'

#     average_id = fields.Many2one(
#         comodel_name='stock.day.average', string='Average')
