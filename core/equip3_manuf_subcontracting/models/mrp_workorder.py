from odoo import models, fields, api, _


class MrpWorkorderInherit(models.Model):
    _inherit = 'mrp.workorder'

    force_qty = fields.Float()
    is_a_subcontracting = fields.Boolean(string='Subcontracting', default=False)
    qty_production = fields.Float('Original Production Quantity', compute='_compute_qty_production', inverse='_inverse_qty_production', related=None)
    is_start = fields.Boolean('Is Start', compute='get_domain_start', default=False)

    subcon_material_picking_id = fields.Many2one('stock.picking', string='Subcontracting Material Transfer')
    subcon_finished_picking_id = fields.Many2one('stock.picking', string='Subcontracting Finished Goods Transfer')
    subcon_workorder_id = fields.Many2one('mrp.workorder', string='Subcontracting Workorder')

    @api.depends('is_a_subcontracting', 'production_state', 'working_state', 'state', 'is_user_working')
    def get_domain_start(self):
        for rec in self:
            if rec.is_a_subcontracting == True or rec.production_state in ['draft', 'done', 'approval', 'approved',
                'reject'] or rec.working_state == 'blocked' or rec.state not in ['ready', 'progress', 'pause'] or rec.is_user_working != False:
                rec.is_start = True
            else:
                rec.is_start = False

    @api.depends('production_id', 'force_qty')
    def _compute_qty_production(self):
        for wo in self:
            if wo.force_qty:
                wo.qty_production = wo.force_qty
                continue
            wo.qty_production = 0.0
            if wo.production_id:
                wo.qty_production = wo.production_id.product_qty

    def _inverse_qty_production(self):
        pass

    def _prepare_consumption_vals(self):
        values = super(MrpWorkorderInherit, self)._prepare_consumption_vals()
        if self.is_a_subcontracting:
            picking = self.subcon_material_picking_id or self.subcon_finished_picking_id
            values.update({
                'is_a_subcontracting': True,
                'finished_qty': picking.subcon_qty_producing,
                'requisition_id': picking.subcon_requisition_id,
                'purchase_id': picking.purchase_id.id
            })
        return values

    def create_consumption(self, confirm_and_assign=False):
        if self.is_a_subcontracting:
            consumption_id = self.env['mrp.consumption'].create(self._prepare_consumption_vals())
            return consumption_id
        return super(MrpWorkorderInherit, self).create_consumption(confirm_and_assign=confirm_and_assign)

    def _split(self, purchase):
        self.ensure_one()

        if self.state not in ('pending', 'ready'):
            return

        to_split_qty = purchase.subcon_product_qty
        subcon_location = self.company_id.subcontracting_warehouse_id.lot_stock_id

        new_ratio = to_split_qty / self.qty_production
        old_ratio = (self.qty_production - to_split_qty) / self.qty_production

        new_workorder = self.env['mrp.workorder']

        if to_split_qty < self.qty_production:
            new_move_raw = self.env['stock.move']
            new_move_byproduct = self.env['stock.move']
            new_move_finished = self.env['stock.move']
            for move in self.move_raw_ids | self.move_finished_ids:
                new_move = move.copy({
                    'product_uom_qty': old_ratio * move.product_uom_qty,
                    'allocated_cost': old_ratio * move.allocated_cost,
                })
                if new_move.raw_material_production_id:
                    new_move_raw |= new_move
                elif new_move.production_id:
                    if new_move.byproduct_id:
                        new_move_byproduct |= new_move
                    elif new_move.finished_id:
                        new_move_finished |= new_move

            force_qty = self.qty_production - to_split_qty
            new_workorder = self.copy({
                'force_qty': force_qty,
                'production_id': self.production_id.id,
                'move_raw_ids': [(6, 0, new_move_raw.ids)],
                'byproduct_ids': [(6, 0, new_move_byproduct.ids)],
                'move_finished_ids': [(6, 0, new_move_finished.ids)]
            })

        self.write({
            'is_a_subcontracting': True,
            'force_qty': to_split_qty,
            'location_id': subcon_location.id,
            'subcon_workorder_id': new_workorder.id,
            'move_raw_ids': [(1, move.id, {
                'product_uom_qty': new_ratio * move.product_uom_qty,
                'location_id': subcon_location.id
            }) for move in self.move_raw_ids],
            'byproduct_ids': [(1, move.id, {
                'product_uom_qty': new_ratio * move.product_uom_qty,
                'allocated_cost': new_ratio * move.allocated_cost
            }) for move in self.byproduct_ids],
            'move_finished_ids': [(1, move.id, {
                'product_uom_qty': new_ratio * move.product_uom_qty,
                'allocated_cost': new_ratio * move.allocated_cost
            }) for move in self.move_finished_ids.filtered(lambda o: o.finished_id)],
        })

        return new_workorder

    def _is_last_workorder(self):
        self.ensure_one()
        if self.is_a_subcontracting:
            not_subcontracting_workorders = self.production_id.workorder_ids.filtered(lambda o: not o.is_a_subcontracting)
            if not_subcontracting_workorders:
                return not_subcontracting_workorders[-1].id == self.subcon_workorder_id.id
            return True
        return super(MrpWorkorderInherit, self)._is_last_workorder()
