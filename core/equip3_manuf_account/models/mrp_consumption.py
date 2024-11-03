import json
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError
from collections import defaultdict
from odoo.tools import float_compare


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'

    valued = fields.Boolean()
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mrp_consumption_id', readonly=True)

    def _pre_button_confirm(self, check_default=True, do_check_consumption=False):
        err_message, action = super(MrpConsumption, self)._pre_button_confirm()
        if err_message or not check_default:
            return err_message, action
        
        # check accounting data
        acc_err_message = self._check_accounting_data()
        if acc_err_message:
            return acc_err_message, False
        
        return err_message, action

    def _action_confirm(self):
        self = self.with_context(force_zero_price_unit=True)
        return super(MrpConsumption, self)._action_confirm()

    def _check_accounting_data(self):
        self.ensure_one()

        err_message = False
        finished_good = self.manufacturing_order_id.product_id
        if not finished_good.categ_id.property_stock_journal:
            err_message = _('Please set Stock Journal for %s first!' % finished_good.name)

        if not finished_good.categ_id.mrp_wip_account_id:
            err_message = _("Please set Manufacturing WiP Account for %s first!" % finished_good.name)

        if not finished_good.categ_id.property_stock_valuation_account_id:
            err_message = _("Please set Stock Valuation Account for %s first!" % finished_good.name)

        for move in self.move_raw_ids | self.byproduct_ids:
            move_product = move.product_id
            if not move_product.categ_id.property_stock_valuation_account_id.id:
                err_message = _("Please set Stock Valuation Account for %s first!" % move_product.name)
                break

        return err_message

    def _get_allocated_cost(self, origin_allocated_cost):
        self.ensure_one()
        production_qty = self.manufacturing_order_id.product_qty
        return float_round((self.product_qty / production_qty) * origin_allocated_cost, precision_digits=2)

    def _finish_workorder(self):
        super(MrpConsumption, self)._finish_workorder()
        if self.is_last_workorder:
            self.manufacturing_order_id._evaluate_valuations()

    def _set_price_unit(self):
        self.ensure_one()

        production = self.manufacturing_order_id
        total_material_cost, byproduct_costs = production._get_and_predict_cost()

        total_byproduct_cost = 0.0
        consumed_byproducts = defaultdict(lambda: 0.0)
        for move in production.move_byproduct_ids.filtered(lambda o: o.state == 'done'):
            move_svls = move.stock_valuation_layer_ids
            svls_qty = abs(sum(move_svls.mapped('quantity')))

            if move._has_byproduct():
                consumed_byproducts[move.origin_byproduct_id] += svls_qty
            
            total_byproduct_cost += (total_material_cost * move.allocated_cost) / 100

        for move in production.move_byproduct_ids.filtered(lambda o: o.state not in ('done', 'cancel')):
            if move._has_byproduct():
                byproduct = self.env['mrp.bom.byproduct'].browse(move.origin_byproduct_id)
                bom_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                should_consume_qty = byproduct.product_uom_id._compute_quantity(byproduct.product_qty * (bom_qty / production.bom_id.product_qty), move.product_uom)
                if float_compare(move.product_uom_qty, should_consume_qty, precision_rounding=move.product_uom.rounding) >= 0:
                    product_qty = move.product_qty
                    allocated_cost = move.allocated_cost
                else:
                    should_consume_qty = move.product_uom._compute_quantity(should_consume_qty, move.product_id.uom_id)
                    product_qty = should_consume_qty - consumed_byproducts[move.origin_byproduct_id]
                    allocated_cost = (product_qty / should_consume_qty) * byproduct.allocated_cost
            else:
                product_qty = move.product_qty
                allocated_cost = move.allocated_cost

            byproduct_cost = (total_material_cost * allocated_cost) / 100
            
            total_byproduct_cost += byproduct_cost

            if move in self.byproduct_ids:
                move.price_unit = byproduct_cost / product_qty

        for move in self.move_finished_ids:
            finished_cost = ((total_material_cost - total_byproduct_cost) * move.allocated_cost) / 100
            move.price_unit = finished_cost / move.product_qty

    def _prepare_moves(self):
        super(MrpConsumption, self)._prepare_moves()
        self._set_price_unit()
