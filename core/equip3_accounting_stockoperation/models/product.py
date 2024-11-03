# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError
from collections import defaultdict
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    categ_costing_method = fields.Selection(related="categ_id.property_cost_method", readonly=True)

    def _is_cost_per_warehouse(self):
        for product in self:
            product.is_cost_per_warehouse = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse') or False
    
    is_cost_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?", compute="_is_cost_per_warehouse")
    
    def action_product_warehouse_cost(self):
        quant_obj = self.env['stock.quant'].sudo()
        product_id = False
        actions = self.env['ir.actions.act_window']._for_xml_id('equip3_accounting_stockoperation.action_product_warehouse_cost_wizard')
        for prod_tmpl in self:
            product_id =self.env['product.product'].search([('product_tmpl_id','=',prod_tmpl.id)])
            product_id = product_id.mapped('product_variant_id')
            product_id.generate_product_warehouse_cost()
            prod_wh_cost_id = self.env['product.warehouse.cost'].search([('product_id','=',product_id.id)])
            # print(prod_wh_cost_id)
            # Some Locations can have same Warehouse?prod_tmpl
            # for c in prod_wh_cost_id:
            #     for l in c.product_cost_line_ids:
            #         quant = quant_obj.with_context(inventory_mode=True).search([('product_id','=',c.product_id.id),('location_id','=',l.warehouse_id.lot_stock_id.id)])
            #         if not quant:
            #             l.write({'cost':0})
            #         if quant and len(quant) == 1:
            #             if quant.inventory_quantity<= 0:
            #                 l.write({'cost':0})
            actions['context'] = {'product_warehouse_cost_id': prod_wh_cost_id.id}
        return actions


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    product_cost_ids = fields.One2many('product.warehouse.cost', 'product_id', 'Warehouse Cost', readonly=True)

    def action_open_quants(self):
        for product in self:
            # Override to hide the `removal_date` column if not needed.\
            quant_obj = self.env['stock.quant'].sudo()
            prod_wh_cost_id = self.env['product.warehouse.cost'].search([('product_id','=',product.id)])
            for c in prod_wh_cost_id:
                for l in c.product_cost_line_ids:
                    quant = quant_obj.with_context(inventory_mode=True).search([('product_id','=',c.product_id.id),('location_id','=',l.warehouse_id.lot_stock_id.id)])
                    if quant and len(quant) == 1:
                        quant.write({'value':l.cost*quant.inventory_quantity})                        
        return super(ProductProduct,self).action_open_quants()
    
    def generate_product_warehouse_cost(self):
        for product in self:
            prod_wh_cost = self.env['product.warehouse.cost'].search([('product_id','=',product.id)])
            stock_warehouse_ids = self.env['stock.warehouse'].search([])
            if prod_wh_cost:
                already_wh_in_cost_lines = [x.warehouse_id.id for x in prod_wh_cost.product_cost_line_ids]
                new_cost_lines = []
                for wh1 in stock_warehouse_ids:
                    if wh1.id not in already_wh_in_cost_lines:
                        new_cost_lines.append((0,0,{'warehouse_id': wh1.id, 'cost': 0}))
                if new_cost_lines:
                    prod_wh_cost.write({'product_cost_line_ids': new_cost_lines})
            else:
                prod_wh_cost_lines = []
                for wh in stock_warehouse_ids:
                    prod_wh_cost_lines.append((0,0,{'warehouse_id': wh.id, 'cost': 0}))
                prod_wh_cost = self.env['product.warehouse.cost'].create({'product_id': product.id, 'product_cost_line_ids': prod_wh_cost_lines})

            costs = self.get_cost_per_warehouse(product=product)
            for line in prod_wh_cost.product_cost_line_ids:
                if line.warehouse_id.id in costs:
                    if line.cost != costs[line.warehouse_id.id]:
                        line.cost = costs[line.warehouse_id.id]
        return prod_wh_cost

    def get_cost_per_warehouse(self, product=False, warehouse=False):
        costs = {}
        if warehouse:
            where_warehouse = """sw.id = %s""" % (warehouse.id,)
        else:
            where_warehouse = """sw.id notnull"""
        if product:
            sql = """SELECT pp.default_code as product, sw.name as warehouse, pp.id as product_id, sw.id as warehouse_id,
                     CASE WHEN sum(svl.quantity) = 0 THEN 0 ELSE sum(svl.value)/sum(svl.quantity) END as cost
                     from stock_valuation_layer svl
                     inner join stock_warehouse sw on sw.id = svl.warehouse_id
                     inner join product_product pp on pp.id = svl.product_id
                     where pp.id = %s
                     and %s
                     group by pp.id, sw.id
                     order by pp.default_code, sw.name""" % (product.id, where_warehouse,)
            self.env.cr.execute(sql)
            cost_fetch = self.env.cr.dictfetchall()
            for x in cost_fetch:
                costs[x['warehouse_id']] = x['cost']
        return costs
    
    
    def _prepare_out_svl_vals_per_wh(self, quantity, company, warehouse):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        context = dict(self._context or {})

        if self.cost_method in ['standard']:
                for move in self.stock_move_ids:
                        unit_cost = move.price_unit 

        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity

        # Get standard_price from 'Product Warehouse Cost' Table
        # self.env.cr.execute("""SELECT COALESCE(SUM(l.cost), 0.00)
        #                         FROM product_warehouse_cost_line AS l
        #                         LEFT JOIN product_warehouse_cost AS p ON p.id=l.prod_wh_cost_id
        #                         WHERE p.product_id = %s
        #                         AND l.warehouse_id = %s
        #                         """,(self.id,warehouse.id))     
        # cost_lines = self.env.cr.fetchall()
        # standard_price = cost_lines and cost_lines[0] and cost_lines[0][0] or 0
        standard_price = 0
        if warehouse:
            costs = self.get_cost_per_warehouse(product=self, warehouse=warehouse)
            if warehouse.id in costs:
                standard_price = costs[warehouse.id]

        # If we fill Unit Price in Inventory Adjustment
        if context.get('inventory_id') and context.get('current_price_unit'):
            standard_price = context.get('current_price_unit')
        
        vals = {
                'product_id' : self.id,
                'value': quantity * standard_price,
                'unit_cost': standard_price,
                'quantity': quantity,
        }
        if self.cost_method in ('average', 'fifo'):
                fifo_vals = self._run_fifo_per_wh(abs(quantity), company, warehouse)
                vals['remaining_qty'] = fifo_vals.get('remaining_qty')
                if self.cost_method == 'fifo':
                        vals.update(fifo_vals)
        return vals
    
    def _run_fifo_per_wh(self, quantity, company, warehouse):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        domain = [
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', company.id),
        ]

        candidates = self.env['stock.valuation.layer'].sudo().search(domain)
        new_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        
        for candidate in candidates:
            if warehouse and candidate.warehouse_id.id == warehouse.id:

                qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

                candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty

                new_standard_price = candidate_unit_cost
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': new_remaining_value,
                }

                candidate.write(candidate_vals)

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate

                if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                    if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                        next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                        new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                    break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
            }
        return vals

    def _run_fifo_vacuum_per_wh(self, warehouse, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        self.ensure_one()
        if company is None:
            company = self.env.company
        svls_to_vacuum = self.env['stock.valuation.layer'].sudo().search([
            ('product_id', '=', self.id),
            ('remaining_qty', '<', 0),
            ('stock_move_id', '!=', False),
            ('company_id', '=', company.id),
        ], order='create_date, id')
        if not svls_to_vacuum:
            return

        domain = [
            ('company_id', '=', company.id),
            ('product_id', '=', self.id),
            ('remaining_qty', '>', 0),
            ('create_date', '>=', svls_to_vacuum[0].create_date),
        ]
        all_candidates = self.env['stock.valuation.layer'].sudo().search(domain)

        for svl_to_vacuum in svls_to_vacuum:
            if svl_to_vacuum.warehouse_id_id.id == warehouse.id:
                # We don't use search to avoid executing _flush_search and to decrease interaction with DB
                candidates = all_candidates.filtered(
                    lambda r: r.create_date > svl_to_vacuum.create_date
                    or r.create_date == svl_to_vacuum.create_date
                    and r.id > svl_to_vacuum.id
                )
                if not candidates:
                    break
                qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
                qty_taken_on_candidates = 0
                tmp_value = 0
                for candidate in candidates:
                    if candidate.warehouse_id_id.id == warehouse.id:
                        qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                        qty_taken_on_candidates += qty_taken_on_candidate

                        candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                        value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                        value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                        new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                        candidate_vals = {
                            'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                            'remaining_value': new_remaining_value
                        }
                        candidate.write(candidate_vals)
                        if not (candidate.remaining_qty > 0):
                            all_candidates -= candidate

                        qty_to_take_on_candidates -= qty_taken_on_candidate
                        tmp_value += value_taken_on_candidate
                        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                            break

                # Get the estimated value we will correct.
                remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
                new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
                corrected_value = remaining_value_before_vacuum - tmp_value
                svl_to_vacuum.write({
                    'remaining_qty': new_remaining_qty,
                })

                # Don't create a layer or an accounting entry if the corrected value is zero.
                if svl_to_vacuum.currency_id.is_zero(corrected_value):
                    continue

                corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
                move = svl_to_vacuum.stock_move_id
                vals = {
                    'product_id': self.id,
                    'value': corrected_value,
                    'unit_cost': 0,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'stock_move_id': move.id,
                    'company_id': move.company_id.id,
                    'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
                    'stock_valuation_layer_id': svl_to_vacuum.id,
                }
                vacuum_svl = self.env['stock.valuation.layer'].sudo().create(vals)

                # Create the account move.
                if self.valuation != 'real_time':
                    continue
                vacuum_svl.stock_move_id._account_entry_move(
                    vacuum_svl.quantity, vacuum_svl.description, vacuum_svl.id, vacuum_svl.value
                )
                # Create the related expense entry
                self._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)

        # If some negative stock were fixed, we need to recompute the standard price.
        product = self.with_company(company.id)
        if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=self.uom_id.rounding):
            product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})