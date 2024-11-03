from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools import float_is_zero


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    @api.depends('consumption_ids', 'consumption_ids.state', 'production_state', 'state')
    def _compute_should_hide_duration(self):
        for workorder in self:
            if workorder.production_state in ('draft', 'approval', 'approved', 'reject'):
                should_hide_duration = True
            else:
                should_hide_duration = any(cons.state == 'approval' for cons in workorder.consumption_ids)
            workorder.should_hide_duration = should_hide_duration

    consumption_ids = fields.One2many('mrp.consumption', 'workorder_id', 'Production Records', readonly=True)
    should_hide_duration = fields.Boolean(compute=_compute_should_hide_duration)

    """ Technical fields. See stock_move.py """
    origin_operation_id = fields.Integer(default=0)

    def name_get(self):
        result = []
        for record in self:
            result += [(record.id, "%s - %s" % (record.workorder_id, record.name))]
        return result

    def button_start(self):
        res = super(MrpWorkorder, self).button_start()
        self.qty_producing = self.qty_remaining
        return res

    def should_process_consumption(self):
        self.ensure_one()
        consumption_ids = self.consumption_ids.filtered(lambda c: c.state == 'confirm')
        finished_qty = sum(consumption_ids.mapped('finished_qty'))
        rejected_qty = sum(consumption_ids.mapped('rejected_qty'))
        return finished_qty + rejected_qty < self.qty_production

    def button_finish_wizard(self):
        self.ensure_one()
        if self.should_process_consumption():
            consumption_id = self.get_consumption_id(confirm_and_assign=True)
            return self.action_open_consumption(res_id=consumption_id.id)

    def action_open_consumption(self, res_id=False):
        self = self.with_context(pop_back=True)
        return {
            'name': _('Production Record'),
            'view_mode': 'form',
            'res_model': 'mrp.consumption',
            'view_id': self.env.ref('equip3_manuf_operations_contd.mrp_consumption_form').id,
            'res_id': res_id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new'
        }

    def _is_last_workorder(self):
        self.ensure_one()
        return self.production_id.workorder_ids[-1].id == self.id

    def _get_mpr_move_raw_vals(self, bom_product_qty, bom_product_uom, bom_lines):
        self.ensure_one()
        production = self.production_id
        move_raw_ids = self.move_raw_ids.filtered(lambda m: not m.mrp_consumption_id)
        manual_moves = move_raw_ids.filtered(lambda m: not m._has_bom_line())
        move_values = [(4, move.id) for move in manual_moves]

        for line in bom_lines:
            bom_line = self.env['mrp.bom.line'].browse(line['id'])
            bom_line_product = self.env['product.product'].browse(line['product_id']['id'])
            bom_line_product_qty = line['product_qty']
            bom_line_product_uom = self.env['uom.uom'].browse(line['product_uom_id']['id'])
            bom_line_operation_id = line['operation_id']['id']

            if bom_line_operation_id != self.origin_operation_id:
                continue

            factor = production.product_uom_id._compute_quantity(self.qty_remaining, bom_product_uom)
            qty_to_create =  bom_line_product_qty * (factor / bom_product_qty)
            
            created_moves = move_raw_ids.filtered(lambda m: m.origin_bom_line_id == line['id'])
            if created_moves:
                move_values += [(4, move.id) for move in created_moves]
            else:
                # keep operation_id False when it's not exist
                operation_id = self.env['mrp.routing.workcenter'].search([('id', '=', bom_line_operation_id)])
                raw_value = production._get_move_raw_values(bom_line_product, qty_to_create, bom_line_product_uom, operation_id.id, bom_line)
                raw_value.update({
                    'origin_bom_line_id': line['id'],
                    'origin_operation_id': bom_line_operation_id
                })
                move_values += [(0, 0, raw_value)]
        return move_values

    def _byproduct_update(self, line):
        # inherited in manuf_account
        self.ensure_one()
        return {
            'origin_byproduct_id': line['id'],
        }

    def _get_mpr_byproduct_vals(self, bom_product_qty, bom_product_uom, byproducts):
        self.ensure_one()
        move_values = [(6, 0, [])]
        if self._is_last_workorder():
            production = self.production_id
            byproduct_ids = self.byproduct_ids.filtered(lambda m: not m.mrp_consumption_byproduct_id)
            manual_moves = byproduct_ids.filtered(lambda m: not m._has_byproduct())
            move_values = [(4, move.id) for move in manual_moves]

            for line in byproducts:
                byproduct = self.env['mrp.bom.byproduct'].browse(line['id'])
                byproduct_product_id = line['product_id']['id']
                byproduct_product_qty = line['product_qty']
                byproduct_product_uom_id = line['product_uom_id']['id']

                factor = production.product_uom_id._compute_quantity(self.qty_remaining, bom_product_uom)
                qty_to_create = byproduct_product_qty * (factor / bom_product_qty)
                
                created_moves = byproduct_ids.filtered(lambda m: m.origin_byproduct_id == line['id'])
                if created_moves:
                    move_values += [(4, move.id) for move in created_moves]
                else:
                    operation_id = production.bom_id.operation_ids[-1]
                    byproduct_value = production._get_move_finished_values(byproduct_product_id, qty_to_create, byproduct_product_uom_id, operation_id.id, byproduct.id)
                    byproduct_value.update(self._byproduct_update(line))
                    move_values += [(0, 0, byproduct_value)]
        return move_values

    def _finished_update(self, line):
        # inherited in manuf_account
        self.ensure_one()
        return {
            'origin_finished_id': line['id']
        }

    def _get_mpr_move_finished_vals(self, bom_product_qty, bom_product_uom, finisheds):
        self.ensure_one()
        move_values = [(6, 0, [])]
        if self._is_last_workorder():
            production = self.production_id
            finished_ids = self.move_finished_ids.filtered(lambda m: not m.byproduct_id and not m.mrp_consumption_finished_id)
            manual_moves = finished_ids.filtered(lambda m: not m._has_finished_line())
            move_values = [(4, move.id) for move in manual_moves]

            for line in finisheds:
                finished = self.env['mrp.bom.finished'].browse(line['id'])
                finished_product_id = line['product_id']['id']
                finished_product_qty = line['product_qty']
                finished_product_uom_id = line['product_uom_id']['id']

                factor = production.product_uom_id._compute_quantity(self.qty_remaining, bom_product_uom)
                qty_to_create = finished_product_qty * (factor / bom_product_qty)
                
                created_moves = finished_ids.filtered(lambda m: m.origin_finished_id == line['id'])
                if created_moves:
                    move_values += [(4, move.id) for move in created_moves]
                else:
                    finished_value = production.with_context(finished_id=finished.id)._get_move_finished_values(finished_product_id, qty_to_create, finished_product_uom_id)
                    finished_value.update(self._finished_update(line))
                    move_values += [(0, 0, finished_value)]
        return move_values

    def _prepare_consumption_vals(self):
        self.ensure_one()

        approval_matrix_id = False
        if self.env.company.production_record_conf:
            approval_matrix_id = self.env['mrp.consumption']._default_approval_matrix(company=self.company_id, branch=self.branch_id)
            if not approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Production Record first!'))
        
        bom_data = self.production_id._read_bom_data(origin=True)[self.production_id.bom_id.id]
        bom_product_qty = bom_data['product_qty']
        bom_product_uom = self.env['uom.uom'].browse(bom_data['product_uom_id']['id'])

        move_raw_values = self._get_mpr_move_raw_vals(bom_product_qty, bom_product_uom, bom_data['bom_line_ids'])
        byproduct_values = self._get_mpr_byproduct_vals(bom_product_qty, bom_product_uom, bom_data['byproduct_ids'])
        move_finished_values = self._get_mpr_move_finished_vals(bom_product_qty, bom_product_uom, bom_data['finished_ids'])

        return {
            'manufacturing_plan': self.mrp_plan_id.id,
            'create_date': fields.Datetime.now(),
            'create_uid': self.env.uid,
            'manufacturing_order_id': self.production_id.id,
            'workorder_id': self.id,
            'product_id': self.product_id.id,
            'finished_qty': self.qty_remaining,
            'rejected_qty': 0.0,
            'date_finished': fields.Datetime.now(),
            'is_last_workorder': self._is_last_workorder(),
            'move_raw_ids': move_raw_values,
            'move_finished_ids': move_finished_values,
            'byproduct_ids': byproduct_values,
            'product_uom_id': self.product_uom_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'approval_matrix_id': approval_matrix_id,
            'is_locked': self.env.user.has_group('mrp.group_locked_by_default'),
            'is_dedicated': self.env.company.dedicated_material_consumption
        }

    def create_consumption(self, confirm_and_assign=False):
        consumption_id = self.env['mrp.consumption'].create(self._prepare_consumption_vals())
        if not confirm_and_assign:
            return consumption_id
        draft_moves = (consumption_id.move_raw_ids | consumption_id.byproduct_ids).filtered(lambda m: m.state == 'draft')
        draft_moves._action_confirm()
        confirmed_move_raws = consumption_id.move_raw_ids.filtered(lambda m: m.state == 'confirmed')
        confirmed_move_raws._action_assign()
        for move in consumption_id.move_raw_ids | consumption_id.byproduct_ids | consumption_id.move_finished_ids:
            if not move.move_line_ids:
                values = {'quantity_done': move.product_uom_qty}
                if move.production_id and not move.byproduct_id:
                    values.update({'mpr_finished_qty': move.product_uom_qty})
                move.write(values)
            else:
                quantity_done = sum(move.move_line_ids.mapped('qty_done'))
                if float_is_zero(quantity_done, precision_rounding=move.product_uom.rounding):
                    for move_line in move.move_line_ids:
                        move_line.write({'qty_done': move_line.product_uom_qty})
        return consumption_id

    def get_consumption_id(self, confirm_and_assign=False):
        self.ensure_one()
        consumption_ids = self.consumption_ids.filtered(lambda c: c.state not in ('confirm', 'reject'))
        if not consumption_ids:
            return self.create_consumption(confirm_and_assign=confirm_and_assign)
        return consumption_ids[0]
