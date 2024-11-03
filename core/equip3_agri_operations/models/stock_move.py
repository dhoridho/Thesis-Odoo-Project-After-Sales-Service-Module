from odoo import models, fields, api, _
from odoo.tools import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('daily_activity_material_id', 'daily_activity_material_id.line_ids', 'daily_activity_harvest_id', 'daily_activity_harvest_id.line_ids')
    def _compute_allowed_activity_lines(self):
        for record in self:
            daily_activity_id = record.daily_activity_material_id or record.daily_activity_harvest_id
            line_ids = []
            if daily_activity_id:
                line_ids = daily_activity_id.line_ids.ids
            record.allowed_activity_line_ids = [(6, 0, line_ids)]

    agri_product_tracking = fields.Selection(related='product_id.tracking')

    activity_line_sequence = fields.Integer()
    block_id = fields.Many2one('crop.block', string='Block')
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-block')

    bunch = fields.Integer(string='Bunch', default=1)

    allowed_activity_line_ids = fields.Many2many('agriculture.daily.activity.line', compute=_compute_allowed_activity_lines)

    # inverse material fields
    daily_activity_material_id = fields.Many2one('agriculture.daily.activity', string='Material Plantation Plan')
    activity_material_id = fields.Many2one('crop.activity.material', string='Activity Material')
    activity_line_material_id = fields.Many2one('agriculture.daily.activity.line', string='Material Plantation Lines')
    activity_record_material_id = fields.Many2one('agriculture.daily.activity.record', string='Material Plantation Record')
    
    # inverse harvest fields
    daily_activity_harvest_id = fields.Many2one('agriculture.daily.activity', string='Harvest Plan')
    activity_harvest_id = fields.Many2one('crop.activity.harvest', string='Crop')
    activity_line_harvest_id = fields.Many2one('agriculture.daily.activity.line', string='Harvest Lines')
    activity_record_harvest_id = fields.Many2one('agriculture.daily.activity.record', string='Harvest Record')

    # inverse transfer moves
    activity_record_transfer_id = fields.Many2one('agriculture.daily.activity.record')

    # inverse planting moves
    adjustment_id = fields.Many2one('agri.crop.adjusted')
    activity_plan_planting_id = fields.Many2one('agriculture.daily.activity')
    activity_line_planting_id = fields.Many2one('agriculture.daily.activity.line')
    activity_record_planting_id = fields.Many2one('agriculture.daily.activity.record')
    nursery_id = fields.Many2one('agriculture.daily.activity.nursery')

    # inverse adjustment moves
    activity_plan_adj_id = fields.Many2one('agriculture.daily.activity')
    activity_line_adj_id = fields.Many2one('agriculture.daily.activity.line')
    activity_record_adj_id = fields.Many2one('agriculture.daily.activity.record')

    stored_availability = fields.Float(string='Forecasted Quantity Stored', compute='_compute_product_availability_stored', store=True)

    crop_id = fields.Many2one('agriculture.crop', string='Crop')
    crop_ids = fields.One2many('agriculture.crop', related='block_id.crop_ids')

    agri_crop_move_plan_id = fields.Many2one('agriculture.daily.activity')
    agri_crop_move_line_id = fields.Many2one('agriculture.daily.activity.line')
    agri_crop_move_record_id = fields.Many2one('agriculture.daily.activity.record')

    crop_line_id = fields.Many2one('agriculture.crop.line', string='Transfer Crop Line')

    harvest_serialize_data = fields.Text()

    def _create_in_svl(self, forced_quantity=None):
        moves_to_exclude = self.filtered(lambda m: m.activity_record_adj_id)
        moves_to_process = self - moves_to_exclude
        moves_to_exclude._create_in_svl_agri_adjustment(forced_quantity=forced_quantity)
        return super(StockMove, moves_to_process)._create_in_svl(forced_quantity=forced_quantity)

    def _create_in_svl_agri_adjustment(self, forced_quantity=None):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = 0.0
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        moves_to_exclude = self.filtered(lambda m: m.activity_record_adj_id)
        moves_to_process = self - moves_to_exclude
        moves_to_exclude._create_out_svl_agri_adjustment(forced_quantity=forced_quantity)
        return super(StockMove, moves_to_process)._create_out_svl(forced_quantity=forced_quantity)

    def _create_out_svl_agri_adjustment(self, forced_quantity=None):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals_agri_adjustment(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _agri_create_in_svl(self):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())

            planting_record_id = move.activity_record_planting_id
            harvest_record_id = move.activity_record_harvest_id
            transfer_record_id = move.activity_record_transfer_id

            activity_record_id = planting_record_id or harvest_record_id
            activity_line_id = activity_record_id.activity_line_id
            daily_activity_id = activity_line_id.daily_activity_id

            material_value = sum(activity_record_id.stock_valuation_layer_ids.filtered(lambda o: o.stock_move_id.activity_record_material_id).mapped('value')) * -1

            fg_value = 0.0
            if planting_record_id:
                fg_value = (move.product_qty / sum(planting_record_id.nursery_ids.mapped('count'))) * material_value
            elif harvest_record_id:
                fg_value = (move.product_qty / sum(harvest_record_id.harvest_ids.mapped('product_qty'))) * material_value
            elif transfer_record_id:
                fg_value = (move.product_qty / sum(transfer_record_id.crop_line_ids.mapped('quantity'))) * material_value
            else:
                continue

            svl_vals.update({
                'daily_activity_id': daily_activity_id.id,
                'activity_line_id': activity_line_id.id,
                'activity_record_id': activity_record_id.id,
                'value': fg_value,
                'unit_cost': fg_value / svl_vals['quantity'],
            })

            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _is_agri_in_moves(self):
        return self.activity_record_planting_id or self.activity_record_harvest_id or self.activity_record_transfer_id

    def _create_in_svl(self, forced_quantity=None):
        agri_fg_moves = self.filtered(lambda o: o._is_agri_in_moves())
        not_agri_fg_moves = self - agri_fg_moves

        agri_fg_svls = agri_fg_moves._agri_create_in_svl()
        not_agri_fg_svls = super(StockMove, not_agri_fg_moves)._create_in_svl(forced_quantity=forced_quantity)
        return agri_fg_svls | not_agri_fg_svls

    def _account_entry_move(self, qty, description, svl_id, cost):
        if self.activity_record_material_id or self.activity_record_harvest_id or self.activity_record_planting_id:
            # create moves from activity record model instead
            return False
        return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

    @api.depends('state', 'product_id', 'product_qty', 'location_id')
    def _compute_product_availability_stored(self):
        for move in self:
            if move.state == 'done':
                move.stored_availability = move.product_qty
            else:
                total_availability = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id) if move.product_id else 0.0
                move.stored_availability = min(move.product_qty, total_availability)

    def _prepare_crop_values(self, activity_record, block_id):
        self.ensure_one()
        crop_values = []
        for move_line in self.move_line_ids:
            crop_values += [{
                'origin': activity_record.name,
                'crop': move_line.product_id.id,
                'block_id': block_id.id,
                'sub_block_id': activity_record.sub_block_id.id,
                'crop_count': move_line.qty_done,
                'crop_date': move_line.date,
                'uom_id': move_line.product_uom_id.id,
                'move_line_id': move_line.id,
                'lot_id': move_line.lot_id.id
            }]
        return crop_values

    def _update_planting_crop_data(self):
        crop_values = []
        for move in self:
            activity_record = move.activity_record_planting_id
            block_id = activity_record.block_id
            crop_values += move._prepare_crop_values(activity_record, block_id)
        if crop_values:
            self.env['agriculture.crop'].create(crop_values)

    def _update_transfer_crop_data(self):
        crop_values = []
        for move in self:
            crop_line = move.crop_line_id
            crop_id = crop_line.crop_id

            crop_id.crop_count -= sum(move.move_line_ids.filtered(lambda o: o.lot_id == crop_id.lot_id).mapped('qty_done'))

            activity_record = move.activity_record_transfer_id
            block_id = crop_line.dest_block_id
            crop_values += move._prepare_crop_values(activity_record, block_id)
            
        if crop_values:
            self.env['agriculture.crop'].create(crop_values)

    def _update_adjustment_crop_data(self):
        for move in self:
            adjustment_id = move.adjustment_id
            activity_record_id = adjustment_id.activity_record_id
            activity_line_id = activity_record_id.activity_line_id
            activity_plan_id = activity_line_id.daily_activity_id

            crop_id = adjustment_id.crop_id
            crop_id.write({
                'crop_count': adjustment_id.counted_qty,
                'history_ids': [(0, 0, {
                    'crop_id': crop_id.id,
                    'activity_plan_id': activity_plan_id.id,
                    'activity_line_id': activity_line_id.id,
                    'activity_record_id': activity_record_id.id,
                    'activity_id': activity_record_id.activity_id.id,
                    'previous_qty': adjustment_id.current_qty,
                    'adjusted_qty': adjustment_id.counted_qty
                })]
            })
            

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        planting_moves = self.filtered(lambda m: m.activity_record_planting_id)
        transfer_moves = self.filtered(lambda m: m.activity_record_transfer_id)
        adjustment_moves = self.filtered(lambda m: m.activity_record_adj_id)

        planting_moves._update_planting_crop_data()
        transfer_moves._update_transfer_crop_data()
        adjustment_moves._update_adjustment_crop_data()
        return res

    def action_agri_show_details(self):
        self.ensure_one()
        if self.agri_product_tracking not in ('lot', 'serial'):
            return
        return {
            'name': _('Lot/Serial Number'),
            'type': 'ir.actions.act_window',
            'res_model': 'agri.move.serializer',
            'target': 'new',
            'view_mode': 'form',
            'context': {'default_move_id': self.id}
        }