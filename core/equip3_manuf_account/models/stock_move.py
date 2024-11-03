from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_round
from collections import defaultdict


class StockMove(models.Model):
    _inherit = 'stock.move'

    allocated_cost = fields.Float(string='Allocated Cost (%)', digits=0)

    def _get_price_unit(self):
        if self.env.context.get('force_zero_price_unit', False):
            price_unit = self.price_unit
            # If the move is a return, use the original move's price unit.
            if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
                price_unit = self.origin_returned_move_id.sudo().stock_valuation_layer_ids[-1].unit_cost
            return price_unit
        return super(StockMove, self)._get_price_unit()

    def _prepare_common_svl_vals(self):
        values = super(StockMove, self)._prepare_common_svl_vals()
        consumption = self._consumption()
        if consumption:
            mrp_type = False
            if self.mrp_consumption_id:
                mrp_type = 'component'
            elif self.mrp_consumption_finished_id:
                mrp_type = 'finished'
            elif self.mrp_consumption_byproduct_id:
                mrp_type = 'byproduct'
            
            values.update({
                'type': mrp_type,
                'mrp_plan_id': consumption.manufacturing_plan.id,
                'mrp_production_id': consumption.manufacturing_order_id.id,
                'mrp_workorder_id': consumption.workorder_id.id,
                'mrp_consumption_id': consumption.id
            })
        return values

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        if self.raw_material_production_id:
            credit_account_id = self.product_id.categ_id.property_stock_valuation_account_id.id
            debit_account_id = self.raw_material_production_id.product_id.categ_id.mrp_wip_account_id.id
        elif self.production_id:
            credit_account_id = self.product_id.categ_id.mrp_wip_account_id.id
            debit_account_id = self.product_id.categ_id.property_stock_valuation_account_id.id
        return super(StockMove, self)._create_account_move_line(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)

    def _compare_expected_moves(self, **kwargs):
        line = kwargs.get('line', {})
        consumption = kwargs.get('consumption', self.env['mrp.consumption'])
        expected_allocated_cost = consumption._get_allocated_cost(line.get('allocated_cost', 0.0))
        return super(StockMove, self)._compare_expected_moves(**kwargs) or expected_allocated_cost != self.allocated_cost

    def _prepare_not_expected_move_values(self, **kwargs):
        self.ensure_one()
        line = kwargs.get('line', {})
        consumption = kwargs.get('consumption', self.env['mrp.consumption'])
        expected_allocated_cost = consumption._get_allocated_cost(line.get('allocated_cost', 0.0))
        
        values = super(StockMove, self)._prepare_not_expected_move_values(**kwargs)
        values.update({
            'expected_allocated_cost': expected_allocated_cost,
            'actual_allocated_cost': self.allocated_cost
        })
        return values

    def  _post_set_mrp_quantites_hook(self, quantity, consumption, line):
        super(StockMove, self)._post_set_mrp_quantites_hook(quantity, consumption, line)
        if self._has_byproduct() or self._has_finished_line():
            self.allocated_cost = consumption._get_allocated_cost(line['allocated_cost'])

    def _production_revaluate_cost(self, company, move_costs):
        total_value = 0.0
        svl_vals_list = []
        for move in self:
            move_svls = move.stock_valuation_layer_ids
            generated_value = sum(move_svls.mapped('value'))
            theoretical_value = move_costs[move.id]
            difference_value = theoretical_value - generated_value

            total_value += theoretical_value

            if company.currency_id.is_zero(difference_value):
                continue

            svls_quantity = sum(move_svls.mapped('quantity'))

            for svl in move_svls:
                line_values = []
                for svl_line in svl.line_ids:
                    svl_line_extra_value = (svl_line.quantity / svls_quantity) * difference_value
                    line_values += [(0, 0, {
                        "stock_move_line_id": svl_line.stock_move_line_id.id,
                        "lot_id": svl_line.lot_id.id,
                        "quantity": 0.0,
                        "unit_cost": 0.0,
                        "value": svl_line_extra_value,
                        "remaining_qty": 0.0,
                        "remaining_value": 0.0
                    })]
                    svl_line.remaining_value += svl_line_extra_value
                
                svl_extra_value = (svl.quantity / svls_quantity) * difference_value
                svl_vals_list += [{
                    "product_id": svl.product_id.id,
                    "value": svl_extra_value,
                    "unit_cost": 0.0,
                    "quantity": 0.0,
                    "remaining_qty": 0.0,
                    "remaining_value": 0.0,
                    "line_ids": line_values,
                    "stock_move_id": svl.stock_move_id.id,
                    "company_id": svl.company_id.id,
                    "description": svl.description,
                    "inventory_id": svl.inventory_id.id,
                    "warehouse_id": svl.warehouse_id.id,
                    "location_id": svl.location_id.id,
                    "lot_ids": [(6, 0, svl.lot_ids.ids)],
                    "type": svl.type,
                    "mrp_plan_id": svl.mrp_plan_id.id,
                    "mrp_production_id": svl.mrp_production_id.id,
                    "mrp_workorder_id": svl.mrp_workorder_id.id,
                    "mrp_consumption_id": svl.mrp_consumption_id.id
                }]
                svl.remaining_value += svl_extra_value

        return total_value, svl_vals_list
