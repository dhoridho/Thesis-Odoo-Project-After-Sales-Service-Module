from odoo import models, fields, api, _
from odoo.addons.mrp.models.mrp_production import MrpProduction as BasicMrpProduction
from odoo.exceptions import ValidationError


# remove `mrp_production_name_uniq` constraint
BasicMrpProduction._sql_constraints = [
    ('qty_positive', 'check (product_qty > 0)', 'The quantity to produce must be positive!'),
]


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'base.synchro.abstract']

    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        if 'product_qty' in vals:
            for plan in self.filtered(lambda o: o.base_sync).mapped('mrp_plan_id'):
                plan_orders = plan.mrp_order_ids
                for line in plan.line_ids:
                    line.to_produce_qty = sum(plan_orders.filtered(lambda o: o in line.order_ids).mapped('product_qty'))

                for material in plan.material_ids:
                    material.to_consume_qty = sum(plan_orders.move_raw_ids.filtered(lambda o: o.product_id == material.product_id).mapped('product_uom_qty'))
        return res

    @api.model
    def _drop_name_unique_constraints(self):
        self.env.cr.execute('ALTER TABLE mrp_production DROP CONSTRAINT IF EXISTS mrp_production_name_uniq')
        self.env.cr.commit()

    @api.constrains('name', 'company_id', 'base_sync')
    def _name_unique_constraints(self):
        orders = self.filtered(lambda o: not o.base_sync)
        for order in orders:
            if self.search([('name', '=', order.name), ('company_id', '=', order.company_id.id), ('id', '!=', order.id), ('base_sync', '=', False)], limit=1):
                raise ValidationError(_('Reference must be unique per Company!'))
    
    def sync_resequence(self):
        orders = self.filtered(lambda o: o.base_sync)
        for order in orders:
            sequence = self.env['stock.picking.type'].search([
                ('code', '=', 'mrp_operation'), 
                ('sequence_code', '=', 'MO')
            ], limit=1).sequence_id
            order.name = sequence.next_by_id()
            order.workorder_ids.sync_resequence()

    def sync_confirm(self):
        orders = self.filtered(lambda o: o.base_sync)
        for order in orders:
            order.action_confirm()
            for move in (order.move_raw_ids | order.move_finished_ids):
                if move.move_line_ids:
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.product_uom_qty
                else:
                    move.quantity_done = move.product_uom_qty
            for workorder in order.workorder_ids:
                workorder.button_start()
                workorder.with_context(doublebook=True).button_finish_wizard()
            order.button_mark_done()

    def sync_unlink(self):
        orders = self.filtered(lambda o: o.base_sync)
        for order in orders:
            plan = order.mrp_plan_id
            if not plan:
                continue
            plan_lines = plan.line_ids.filtered(lambda o: order in o.order_ids)
            qty_to_take = order.product_qty
            for line in plan_lines:
                qty_taken = min(qty_to_take, line.to_produce_qty)
                line.to_produce_qty -= qty_taken
                qty_to_take -= qty_taken
                if qty_to_take <= 0.0:
                    break
            plan_lines.filtered(lambda o: o.to_produce_qty <= 0.0).unlink()

            plan_materials = plan.material_ids
            for move in order.move_raw_ids:
                move_materials = plan_materials.filtered(lambda o: o.product_id == move.product_id)
                if not move_materials:
                    continue
                qty_to_take = move.product_uom_qty
                for material in move_materials:
                    qty_taken = min(qty_to_take, material.to_consume_qty)
                    material.to_consume_qty -= qty_taken
                    qty_to_take -= qty_taken
                    if qty_to_take <= 0.0:
                        break
                move_materials.filtered(lambda o: o.to_consume_qty <= 0.0).unlink()

        orders.workorder_ids.sync_unlink()
        orders.unlink()

    def make_unlink(self):

        def unlink(self):
            if any(production.state == 'done' and not production.base_sync for production in self):
                raise UserError(_('Cannot delete a manufacturing order in done state.'))
            self.action_cancel()
            not_cancel = self.filtered(lambda m: m.state != 'cancel')
            if not_cancel:
                productions_name = ', '.join([prod.display_name for prod in not_cancel])
                raise UserError(_('%s cannot be deleted. Try to cancel them before.', productions_name))

            workorders_to_delete = self.workorder_ids.filtered(lambda wo: wo.state != 'done')
            if workorders_to_delete:
                workorders_to_delete.unlink()
            return super(BasicMrpProduction, self).unlink()

        return unlink

    def _register_hook(self):
        BasicMrpProduction._patch_method('unlink', self.make_unlink())
        return super(MrpProduction, self)._register_hook()


class MrpEstimatedCost(models.Model):
    _name = 'mrp.estimated.cost'
    _inherit = ['mrp.estimated.cost', 'base.synchro.abstract']
