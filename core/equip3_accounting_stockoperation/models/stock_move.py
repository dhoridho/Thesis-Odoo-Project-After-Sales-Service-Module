# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError
from collections import defaultdict


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_cost_price_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?", compute="is_cost_price_per_warehouse")

    def is_cost_price_per_warehouse(self):
        is_cost_price_per_warehouse = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse', False)
        return is_cost_price_per_warehouse

    def _action_done(self):
        for data in self:
            if data.is_cost_price_per_warehouse:
                if data.transfer_id:
                    for move in data.move_lines:
                        move_warehouse_id = move.picking_id.transfer_id.source_warehouse_id.id
                        prod_wh_cost_id =  move.with_company(move.company_id).product_id.product_cost_ids
                        curr_prod_cost = 0
                        if prod_wh_cost_id:
                            prod_wh_cost_line = prod_wh_cost_id.product_cost_line_ids.filtered(lambda line: line.warehouse_id.id == move_warehouse_id)
                            for cost_line in prod_wh_cost_line:
                                curr_prod_cost += cost_line.cost
                        if curr_prod_cost:
                            move.write({'price_unit':curr_prod_cost})
                            move.product_id.write({'standard_price':curr_prod_cost})
        res = super(StockPicking, self)._action_done()
        return res

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    is_cost_price_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?", compute="is_cost_price_per_warehouse")

    def is_cost_price_per_warehouse(self):
        is_cost_price_per_warehouse = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse', False)
        return is_cost_price_per_warehouse


    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    @api.model
    def _create_correction_svl(self, move, diff):
        if self.is_cost_price_per_warehouse:
            stock_valuation_layers = self.env['stock.valuation.layer']
            if (move._is_in() and diff > 0) or (move._is_out() and diff < 0):
                move.product_price_update_before_done(forced_qty=diff)
                forced_qty = move.quantity_done
                if self.is_cost_price_per_warehouse:
                    move.product_price_per_wh_update_before_done(forced_qty=forced_qty)
                stock_valuation_layers |= move._create_in_svl(forced_quantity=abs(diff))
                if move.product_id.cost_method in ('average', 'fifo'):
                    if self.is_cost_price_per_warehouse:
                        move.product_id._run_fifo_vacuum_per_wh(move.location_id.warehouse_id, move.company_id)
                    else:
                        move.product_id._run_fifo_vacuum(move.company_id)
            elif ( move._is_in() and diff < 0) or (move._is_out() and diff > 0):
                stock_valuation_layers |= move._create_out_svl(forced_quantity=abs(diff))
            elif move._is_dropshipped() and diff > 0 or move._is_dropshipped_returned() and diff < 0:
                stock_valuation_layers |= move._create_dropshipped_svl(forced_quantity=abs(diff))
            elif move._is_dropshipped() and diff < 0 or move._is_dropshipped_returned() and diff > 0:
                stock_valuation_layers |= move._create_dropshipped_returned_svl(forced_quantity=abs(diff))
            for svl in stock_valuation_layers:
                if not svl.product_id.valuation == 'real_time':
                    continue
                svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
        else:
            return super(StockMoveLine, self)._create_correction_svl(move, diff)



class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', compute='get_warehouse_id')

    def get_warehouse_id(self):
        for record in self:
            if record.stock_move_id:
                picking_id = record.stock_move_id.picking_id
                if picking_id and picking_id.location_dest_id and picking_id.location_dest_id.usage == 'internal' and picking_id.location_dest_id.warehouse_id:
                    record.warehouse_id = picking_id.location_dest_id.warehouse_id.id
                elif picking_id and picking_id.location_id and picking_id.location_id.usage == 'internal' and picking_id.location_id.warehouse_id:
                    record.warehouse_id = picking_id.location_id.warehouse_id.id
                elif record.stock_move_id.location_id.usage == 'internal':
                    record.warehouse_id = record.stock_move_id.location_id.warehouse_id.id
                elif record.stock_move_id.location_dest_id.usage == 'internal':
                    record.warehouse_id = record.stock_move_id.location_dest_id.warehouse_id.id
                else:
                    record.warehouse_id = False
            else:
                record.warehouse_id = False


class StockMove(models.Model):
    _inherit = "stock.move"

    is_cost_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?", compute="_is_cost_per_warehouse")

    def _is_cost_per_warehouse(self):
        self.is_cost_per_warehouse = eval(self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse') or 'False')


    # def _get_price_unit(self):
    #     """ Returns the unit price to value this stock move """
    #     re =  super(StockMove, self)._get_price_unit()
    #     move = self
    #     prod_wh_cost_id =  move.with_company(move.company_id).product_id.product_cost_ids
    #     is_cost_per_warehouse = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse') or False
    #     if is_cost_per_warehouse:
    #         if self.picking_id.transfer_id:
    #             move_warehouse_id = self.picking_id.transfer_id.source_warehouse_id.id
    #             curr_prod_cost = 0
    #             if prod_wh_cost_id:
    #                 prod_wh_cost_line = prod_wh_cost_id.product_cost_line_ids.filtered(lambda line: line.warehouse_id.id == move_warehouse_id)
    #                 for cost_line in prod_wh_cost_line:
    #                     curr_prod_cost += cost_line.cost
    #             if curr_prod_cost:
    #                 re = curr_prod_cost
    #     return re

    def _action_done(self, cancel_backorder=False):
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            forced_qty = move.quantity_done
            if move.is_cost_per_warehouse:
                valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
                if move.picking_id.transfer_id:
                    if move.location_dest_id.id == move.picking_id.picking_type_id.warehouse_id.lot_stock_id.id:
                        move.product_price_per_wh_update_before_done(forced_qty=forced_qty)
                valued_moves['in'].product_price_per_wh_update_before_done(forced_qty=forced_qty)
        return res

    def prod_price_update_before_done(self, forced_qty=None):
        if self.is_cost_per_warehouse:
            return self.product_price_per_wh_update_before_done(forced_qty=forced_qty)
        else:
            return self.product_price_update_before_done(forced_qty=forced_qty)

    def product_price_update_before_done(self, forced_qty=None):
        for move in self.filtered(lambda move:  move.with_company(move.company_id).product_id.cost_method == 'average'):
            is_in_per_wh = False
            if move._is_in():
                is_in_per_wh = True
            if is_in_per_wh:
                forced_qty = move.quantity_done
                if move.is_cost_per_warehouse:
                    move.product_price_per_wh_update_before_done(forced_qty=forced_qty)
        res = super(StockMove, self).product_price_update_before_done(forced_qty=forced_qty)
        return res


    def product_price_per_wh_update_before_done(self, forced_qty=None):
        quant_obj = self.env['stock.quant'].sudo()
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move.with_company(move.company_id).product_id.cost_method == 'average'):
            is_in_per_wh = False
            if move._is_in():
                is_in_per_wh = True
            if move.picking_id.transfer_id:
                if move.location_dest_id.id == move.picking_id.picking_type_id.warehouse_id.lot_stock_id.id:
                    is_in_per_wh = True
            if not is_in_per_wh:
                continue
            move_warehouse_id = move.picking_id and move.picking_id.location_dest_id.warehouse_id and move.picking_id.location_dest_id.warehouse_id.id or False
            company_id = self.env.company.id
            product_id = move.with_company(move.company_id).product_id.id
            move.with_company(move.company_id).product_id.generate_product_warehouse_cost()
            """Get Product Avg Cost per Warehouse """

            prod_wh_cost_id = self.env['product.warehouse.cost'].search([('product_id','=',product_id)]) or move.with_company(move.company_id).product_id.product_cost_ids
            curr_prod_cost = 0

            if prod_wh_cost_id:
                prod_wh_cost_line = prod_wh_cost_id.product_cost_line_ids.filtered(lambda line: line.warehouse_id.id == move_warehouse_id)
                if prod_wh_cost_line:
                    for cost_line in prod_wh_cost_line:
                        curr_prod_cost += cost_line.cost
                else:
                    prod_wh_cost_id = move.with_company(move.company_id).product_id.generate_product_warehouse_cost()



            """Compute `value_svl` and `quantity_svl`."""
            quantity_svl_per_wh = 0

            domain = [
                ('product_id', '=', product_id),
                ('company_id', '=', company_id),
            ]
            location_dest_id = move.picking_id.location_dest_id
            location_dest_warehouse_id =  location_dest_id and location_dest_id.usage=='internal' and location_dest_id.warehouse_id or False
            if location_dest_warehouse_id:
                domain.append(('warehouse_id','=',location_dest_warehouse_id.id))
            if self.env.context.get('to_date'):
                to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
                domain.append(('create_date', '<=', to_date))
            svl_ids = self.env['stock.valuation.layer'].search(domain)
            quantity_svl_per_wh = 0
            for svl in svl_ids:
                if location_dest_warehouse_id and svl.warehouse_id.id == location_dest_warehouse_id.id:
                    quantity_svl_per_wh += svl.quantity

            product_tot_qty_available = quantity_svl_per_wh + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
            else:
                # Get the standard price
                amount_unit = curr_prod_cost
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)

            tmpl_dict[move.product_id.id] += qty_done
            # Write the standard price to Product Warehouse Cost Line
            # ggg
            if move.picking_id.transfer_id:
                if move.location_dest_id.id == move.picking_id.picking_type_id.warehouse_id.lot_stock_id.id:
                    new_std_price = (move._get_price_unit() * qty)

            for line in prod_wh_cost_id.product_cost_line_ids.filtered(lambda line: line.warehouse_id.id == move_warehouse_id):
                qty_quant = 0
                quant = quant_obj.sudo().with_context(inventory_mode=True).search([('product_id','=',move.product_id.id),('location_id','=',move.location_dest_id.id)])
                if quant and len(quant) == 1:
                    qty_quant = quant.inventory_quantity - qty
                if move.picking_id.transfer_id:
                    new_std_price+=line.cost*qty_quant
                valueNew = new_std_price
                if move.picking_id.transfer_id:
                    if new_std_price and (qty_quant+qty) >0:
                        valueNew = new_std_price/(qty_quant+qty)
                line.write({'cost': valueNew})

                # lllff
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price


    def _create_in_svl(self, forced_quantity=None):

        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        # self.ensure_one()  # Ensure that the method is called on a single record

        svl_vals_list = []
        validity = False
        for move in self:
            move.ensure_one()  # Ensure that the method is called on a single record
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)

            unit_cost = abs(move._get_price_unit())
            if move.is_cost_per_warehouse:
                warehouse = (move.location_dest_id.warehouse_id or move.location_id.warehouse_id)
                if warehouse:
                    costs = move.product_id.get_cost_per_warehouse(product=move.product_id, warehouse=warehouse)
                    if warehouse.id in costs:
                        validity = True
                        unit_cost = costs[warehouse.id]
                # May be negative (i.e. decrease an out move).

            # If we fill Unit Price in Inventory Adjustment
            if move.inventory_id:
                current_price_unit = abs(move._get_inventory_line_price_unit())
                if current_price_unit:
                    validity = True
                    unit_cost = current_price_unit

            # Purchase Order Line Unit Price
            if move.purchase_line_id:
                purchase_line = move.purchase_line_id
                purchase_order = purchase_line.order_id
                price_unit = purchase_line.price_subtotal / purchase_line.product_qty
                unit_cost = purchase_order.currency_id._convert(price_unit, purchase_order.company_id.currency_id, purchase_order.company_id, fields.Date.context_today(self), round=False)
                validity = True
                if move.purchase_line_id.product_uom != move.product_id.uom_id:
                    unit_cost = move.product_id.uom_id._compute_quantity(unit_cost, move.purchase_line_id.product_uom)

            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % (move.picking_id.name or move.name)
            svl_vals.update({'warehouse_id': move.picking_id.location_dest_id.warehouse_id and move.picking_id.location_dest_id.warehouse_id.id or False, 'location_id': move.location_dest_id.id})
            svl_vals_list.append(svl_vals)

        if validity == True:
            return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        return super(StockMove, self)._create_in_svl(forced_quantity=forced_quantity)


    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            if move.is_cost_per_warehouse:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_out_move_lines()
                valued_quantity = 0
                for valued_move_line in valued_move_lines:
                    valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                    continue

                svl_vals = {}
                if move.is_cost_per_warehouse:
                    move.product_id.generate_product_warehouse_cost()
                    svl_vals = move.product_id.with_context({'current_price_unit': move._get_inventory_line_price_unit(), 'inventory_id': move.inventory_id.id,})._prepare_out_svl_vals_per_wh(forced_quantity or valued_quantity, move.company_id, warehouse=move.location_id.warehouse_id)
                else:
                    svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)

                svl_vals.update(move._prepare_common_svl_vals())

                if forced_quantity:
                    svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
                svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
                if not svl_vals.get('location_id'):
                    svl_vals['location_id'] = move.location_id.id
                svl_vals_list.append(svl_vals)
                return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        return super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)

    def _get_inventory_line_price_unit(self):
        current_price_unit = 0
        move = self
        if self.inventory_id and self.product_id:
            self.env.cr.execute("""
                SELECT COALESCE(unit_price, 0)
                from stock_inventory_line
                where inventory_id = %s and product_id = %s
                order by unit_price desc limit 1
            """, (self.inventory_id.id, self.product_id.id,))
            price_get = self.env.cr.fetchone()
            if price_get and price_get[0] and price_get[0] is not None:
                current_price_unit = price_get[0]

        return current_price_unit
