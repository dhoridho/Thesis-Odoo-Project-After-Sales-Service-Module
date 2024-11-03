from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from collections import defaultdict


def _find(lines, line_id):
    for line in lines:
        if line['id'] == line_id:
            return line
    return False


class StockMove(models.Model):
    _inherit = 'stock.move'

    sequence = fields.Integer('Sequence', default=10)
    mrp_consumption_id = fields.Many2one('mrp.consumption', string='Production Record Component')
    mrp_consumption_finished_id = fields.Many2one('mrp.consumption', string='Production Record Finished')
    mrp_consumption_byproduct_id = fields.Many2one('mrp.consumption', string='Production Record ByProduct')
    
    mrp_product_uom_qty = fields.Float(string='Production Quantity', digits='Product Unit of Measure', compute='_compute_production_quantity')
    
    dedicated_qty = fields.Float(string='Dedicated Quantity', digits='Product Unit of Measure')
    is_transfered = fields.Boolean()

    mpr_finished_qty = fields.Float()
    mpr_rejected_qty = fields.Float()
    is_mpr_rejected = fields.Boolean()

    """ Technical fields.
    These fields are intended to store the history of bomline, byproduct & operation.
    Since bom_line_id, byproduct_id and operation_id may be removed from the BoM 
    which will make the relation empty, so these fields are created as integers. 
    Original moves are determined from these fields, see _has_bom_line, _has_byproduct and _is_bom_move bellow."""
    origin_bom_line_id = fields.Integer(default=0)
    origin_byproduct_id = fields.Integer(default=0)
    origin_operation_id = fields.Integer(default=0)
    origin_finished_id = fields.Integer(default=0)

    def _has_bom_line(self):
        self.ensure_one()
        return self.origin_bom_line_id > 0

    def _has_byproduct(self):
        self.ensure_one()
        return self.origin_byproduct_id > 0

    def _has_finished_line(self):
        self.ensure_one()
        return self.origin_finished_id > 0

    def _is_bom_move(self):
        self.ensure_one()
        return self._has_bom_line() or self._has_byproduct() or self._has_finished_line()

    def _consumption(self):
        self.ensure_one()
        return self.mrp_consumption_id or self.mrp_consumption_byproduct_id or self.mrp_consumption_finished_id

    @api.depends('origin_bom_line_id', 'origin_byproduct_id', 'origin_finished_id', 'product_uom_qty', 'product_uom')
    def _compute_production_quantity(self):
        for record in self:
            uom = record.product_uom

            line = False
            if record.origin_bom_line_id:
                line = self.env['mrp.bom.line'].browse(record.origin_bom_line_id)
            elif record.origin_byproduct_id:
                line = self.env['mrp.bom.byproduct'].browse(record.origin_byproduct_id)
            elif record.origin_finished_id:
                line = self.env['mrp.bom.finished'].browse(record.origin_finished_id)
            
            mrp_product_uom_qty = 0.0
            if line and line.exists():
                mrp_product_uom_qty = record.product_uom_qty
            
            record.mrp_product_uom_qty = mrp_product_uom_qty

    @api.onchange('product_uom')
    def _onchange_product_uom_mpr(self):
        self._set_mpr_quantities()

    def _set_mpr_quantities(self):
        moves_todo = self.filtered(lambda m: m._consumption() and m._is_bom_move() and \
            m.product_uom and m.state not in ('done', 'cancel'))

        production_ids = moves_todo.mapped('raw_material_production_id') | self.mapped('production_id')
        if not production_ids:
            return

        bom_datas = production_ids._read_bom_data(origin=True)
        for move in moves_todo:
            production = move.raw_material_production_id or move.production_id
            consumption = move._consumption()

            bom_data = bom_datas[production.bom_id.id]
            bom_product_uom = self.env['uom.uom'].browse(bom_data['product_uom_id']['id'])

            if move._has_bom_line():
                line = _find(bom_data['bom_line_ids'], move.origin_bom_line_id)
            elif move._has_byproduct():
                line = _find(bom_data['byproduct_ids'], move.origin_byproduct_id)
            elif move._has_finished_line():
                line = _find(bom_data['finished_ids'], move.origin_finished_id)
            else:
                continue
            
            line_product_qty = line['product_qty']
            line_product_uom = self.env['uom.uom'].browse(line['product_uom_id']['id'])

            ratio = line_product_qty / bom_data['product_qty']
            quantity = consumption.product_uom_id._compute_quantity(consumption.product_qty, bom_product_uom)
            quantity = line_product_uom._compute_quantity(quantity * ratio, move.product_uom)

            if move._has_finished_line():
                finished_qty = consumption.product_uom_id._compute_quantity(consumption.finished_qty, bom_product_uom)
                finished_qty = line_product_uom._compute_quantity(finished_qty * ratio, move.product_uom)

                rejected_qty = consumption.product_uom_id._compute_quantity(consumption.rejected_qty, bom_product_uom)
                rejected_qty = line_product_uom._compute_quantity(rejected_qty * ratio, move.product_uom)

                move.write({
                    'mpr_finished_qty': finished_qty,
                    'mpr_rejected_qty': rejected_qty
                })
                if float_is_zero(finished_qty + rejected_qty - quantity, precision_rounding=move.product_uom.rounding):
                    quantity = finished_qty

            move._post_set_mrp_quantites_hook(quantity, consumption, line)

    def  _post_set_mrp_quantites_hook(self, quantity, consumption, line):
        self.ensure_one()
        # inherited in manuf_account
        self.quantity_done = quantity

    def _do_unreserve(self):
        result = super(StockMove, self)._do_unreserve()
        self.write({'dedicated_qty': 0.0})
        return result

    def _prepare_move_split_vals(self, qty):
        defaults = super()._prepare_move_split_vals(qty)
        defaults['workorder_id'] = self.workorder_id.id
        return defaults

    def action_show_details(self):
        res = super(StockMove, self).action_show_details()
        if self.env.context.get('back_consumption_id'):
            res['context'].update({'back_consumption_id': self.env.context.get('back_consumption_id')})
        return res

    def action_save(self):
        res = super(StockMove, self).action_save()
        if self.env.context.get('back_consumption_id'):
            return {
                'name': _('Production Record'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.consumption',
                'target': 'new',
                'res_id': self.env.context.get('back_consumption_id'),
            }
        return res

    @api.depends('product_uom_qty', 'raw_material_production_id', 'raw_material_production_id.product_qty',
    'raw_material_production_id.qty_produced', 'production_id', 'production_id.product_qty', 'production_id.qty_produced')
    def _compute_unit_factor(self):
        super(StockMove, self)._compute_unit_factor()
        for move in self:
            move.unit_factor = move.product_uom_qty

    @api.depends('raw_material_production_id.qty_producing', 'product_uom_qty', 'product_uom')
    def _compute_should_consume_qty(self):
        super(StockMove, self)._compute_should_consume_qty()
        for move in self:
            if move.raw_material_production_id:
                move.should_consume_qty = move.product_uom_qty

    def _compare_expected_moves(self, **kwargs):
        # inherited in manuf_account
        self.ensure_one()
        return kwargs.get('expected_qty', 0.0) != self.quantity_done

    def _prepare_not_expected_move_values(self, **kwargs):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'expected_qty': kwargs.get('expected_qty', 0.0),
            'actual_qty': self.quantity_done
        }

    def on_scaled(self):
        super(StockMove, self).on_scaled()
        action = None
        if self.mrp_consumption_id and self.env.context.get('pop_back', False):
            action = self.mrp_consumption_id.workorder_id.action_open_consumption(res_id=self.mrp_consumption_id.id)
            action['views'] = [[action['view_id'], action['view_mode']]]
        return action

    def _quantity_done_set(self):
        if not self.env.context.get('scaling', False):
            return super(StockMove, self)._quantity_done_set()

        quantity_done = self[0].quantity_done  # any call to create will invalidate `move.quantity_done`
        for move in self:
            move_lines = move._get_move_lines()
            if not move_lines:
                if quantity_done:
                    # do not impact reservation here
                    move_line = self.env['stock.move.line'].create(dict(move._prepare_move_line_vals(), qty_done=quantity_done))
                    move.write({'move_line_ids': [(4, move_line.id)]})
            elif len(move_lines) == 1:
                move_lines[0].qty_done = quantity_done
            else:
                qty_remaining = quantity_done
                for move_line in move_lines:
                    if not float_is_zero(qty_remaining, precision_rounding=move.product_uom.rounding):
                        if move_line.product_id.tracking == 'serial':
                            qty = 1.0
                        else:
                            qty = quantity_done
                        move_line.qty_done = qty
                        qty_remaining -= qty
                    else:
                        move_line.qty_done = 0.0
