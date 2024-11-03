import json
from odoo import models, fields, api, _
from collections import defaultdict
from odoo.tools import float_is_zero
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    # technical fields
    inventory_line_int = fields.Integer()

    def _warehouse_id(self):
        self.ensure_one()
        return self.env['stock.location'].browse(self._location_id()).get_warehouse().id

    def _location_id(self):
        self.ensure_one()
        location = self.env['stock.location']
        if self._is_in():
            location = self.location_dest_id
        elif self._is_out():
            location = self.location_id
        return location.id

    def _ordered_lots(self):
        lot_ids = []
        for move in self:
            move_lines = move._get_valued_move_lines()
            for lot_id in move_lines._ordered_lots():
                if lot_id not in lot_ids:
                    lot_ids += [lot_id]
        return lot_ids

    @api.model
    def _get_freezed_inventories_where(self, inventory_ids=None):
        where_clause = ["si.state NOT IN ('draft', 'done')"]
        query_params = []

        if inventory_ids:
            where_clause += ['si.id NOT IN %s']
            query_params += [tuple(inventory_ids)]

        return where_clause, query_params

    @api.model
    def _get_freezed_inventories(self, inventory_ids=None):
        where_clause = ["si.state NOT IN ('draft', 'done')"]
        query_params = []

        if inventory_ids:
            where_clause += ['si.id NOT IN %s']
            query_params += [tuple(inventory_ids)]

        where_clause, query_params = self._get_freezed_inventories_where(inventory_ids=inventory_ids)
        where_clause = ' AND '.join(where_clause)
        
        self.env.cr.execute("""
        SELECT
            sil.location_id AS location_id,
            STRING_AGG(DISTINCT(si.{field_name})::character varying, ',') AS inventory_names
        FROM
            stock_inventory_line sil
        LEFT JOIN
            stock_inventory si
            ON (si.id = sil.inventory_id)
        WHERE
            {where_clause}
        GROUP BY
            sil.location_id
        """.format(where_clause=where_clause, field_name=self.env['stock.inventory']._rec_name), query_params)

        return {o[0]: ', '.join((o[1] or '').split(',')) for o in self.env.cr.fetchall()}

    def _get_freezed_locations(self):
        inventory_ids = self.mapped('inventory_id').ids
        return self._get_freezed_inventories(inventory_ids)

    def _check_freeze(self):
        freezed_locations = self._get_freezed_locations()
        for move in self:
            if move.location_id.id in freezed_locations:
                freeze_source = freezed_locations[move.location_id.id]
                raise ValidationError(_("Can't move product %s from location %s, because the location is in freeze status from %s. Stock move can be process after operation is done." % (move.product_id.display_name, move.location_id.display_name, freeze_source)))
            elif move.location_dest_id.id in freezed_locations:
                freeze_source = freezed_locations[move.location_dest_id.id]
                raise ValidationError(_("Can't move product %s to location %s, because the location is in freeze status from %s. Stock move can be process after operation is done." % (move.product_id.display_name, move.location_dest_id.display_name, freeze_source)))

    def _action_done(self, cancel_backorder=False):
        if self: # sometimes self is empty, avoid operations
            self._check_freeze()

        self = self.with_context(active_stock_moves=self)
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        self.filtered(lambda o: o._is_in() and o.product_id.cost_method == 'average').product_price_update_after_done()
        return res

    def _prepare_common_svl_vals(self):
        vals = super(StockMove, self)._prepare_common_svl_vals()
        vals.update({
            'inventory_id': self.inventory_id.id,
            'warehouse_id': self._warehouse_id(),
            'location_id': self._location_id(),
            'lot_ids': [(6, 0, self.lot_ids.ids)]
        })
        return vals

    def _get_valued_move_lines(self):
        move_lines = self.env['stock.move.line']
        for valued_type in self._get_valued_types():
            if getattr(self, '_is_%s' % valued_type)():
                move_lines |= getattr(self, '_get_%s_move_lines' % valued_type)()
        return move_lines

    def _get_lot_move_lines_dict(self, forced_move_lines=None):
        move_lines = forced_move_lines or self._get_valued_move_lines()
        lot_dict = {}
        for move_line in move_lines:
            lot_id = move_line.lot_id.id
            if lot_id not in lot_dict:
                lot_dict[lot_id] = [move_line.id]
            else:
                lot_dict[lot_id] += [move_line.id]
        return lot_dict

    def _get_dropshipped_move_lines(self):
        """
        _is_dropshipped() determined via stock.move locations not stock.move.line,
        So, no need to filter locations on move_line_ids
        """
        return self.move_line_ids

    def _get_dropshipped_returned_move_lines(self):
        """
        _is_dropshipped_returned() determined via stock.move locations not stock.move.line,
        So, no need to filter locations on move_line_ids
        """
        return self.move_line_ids
    

    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)

            if is_cost_per_warehouse:
                move = move.with_context(price_for_warehouse=move._warehouse_id())

            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id.with_context(move=move)._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())

            # TODO: FIX THIS
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo()._query_create(svl_vals_list)

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)

            if is_cost_per_warehouse:
                move = move.with_context(price_for_warehouse=move._warehouse_id())
            
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id.with_context(move=move)._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            
            # TODO: FIX THIS
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo()._query_create(svl_vals_list)

    def product_price_update_get_price_unit(self):
        self.ensure_one()
        return self._get_price_unit()

    def product_price_update_before_done(self, forced_qty=None):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        groupby = ['product_id']
        if is_cost_per_warehouse:
            groupby += ['warehouse_id']
        
        svl_dict = self.mapped('product_id')._query_svl(self.env.company, groupby=groupby)

        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self:
            if not move._is_in():
                continue

            cost_method = move.with_company(move.company_id).product_id.cost_method
            rounding = move.product_id.uom_id.rounding

            key = move.product_id.id
            if is_cost_per_warehouse:
                move_warehouse_id = move._warehouse_id()
                key = (move.product_id.id, move_warehouse_id)
                move = move.with_context(price_for_warehouse=move_warehouse_id)

            product_qty_svl = svl_dict.get(key, {}).get('quantity', 0.0)

            if cost_method == 'average':
                product_tot_qty_available = product_qty_svl + tmpl_dict[move.product_id.id]

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
                    amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).standard_price
                    new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)

                tmpl_dict[move.product_id.id] += qty_done
                # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
                move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().standard_price = new_std_price
                std_price_update[move.company_id.id, move.product_id.id] = new_std_price

            elif cost_method == 'fifo':
                # adapt standard price on incomming moves if the product cost_method is 'fifo'
                if float_is_zero(product_qty_svl, precision_rounding=rounding):
                    new_std_price = move.product_price_update_get_price_unit()
                    move.product_id.with_company(move.company_id.id).sudo().standard_price = new_std_price

    def product_price_update_after_done(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        if is_cost_per_warehouse:
            return
        
        for product in self.mapped('product_id'):
            """ Let's _change_standard_price do the job """
            product.with_context(is_product_price_update=True)._change_standard_price(product.standard_price)

    def do_pending_valuations(self):
        self = self.with_context(active_stock_moves=self)

        valued_moves = {valued_type: self.env['stock.move'].with_context(self.env.context) for valued_type in self._get_valued_types()}
        for move in self:
            if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                continue
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        valued_moves['in'].product_price_update_before_done()

        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

        for svl in stock_valuation_layers:
            if not svl.product_id.valuation == 'real_time':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)

        stock_valuation_layers._check_company()

        # For every in move, run the vacuum for the linked product.
        products_to_vacuum = valued_moves['in'].mapped('product_id')
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
        for product_to_vacuum in products_to_vacuum:
            product_to_vacuum._run_fifo_vacuum(company)

        self.filtered(lambda o: o._is_in() and o.product_id.cost_method == 'average').product_price_update_after_done()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        self.ensure_one()

        value = quantity * unit_cost
        values = {
            'stock_move_line_id': self.id,
            'lot_id': self.lot_id.id,
            'quantity': quantity,
            'unit_cost': unit_cost,
            'value': value
        }
        if self.product_id.cost_method in ('average', 'fifo'):
            values.update({
                'remaining_qty': quantity,
                'remaining_value': value
            })
        return values

    def _prepare_out_svl_vals(self, quantity, fifo_vals):
        self.ensure_one()

        factor = -1 if quantity > 0 else 1
        values = {
            'stock_move_line_id': self.id,
            'lot_id': self.lot_id.id,
            'quantity': factor * quantity,
            'unit_cost': fifo_vals['unit_cost'],
            'value': factor * quantity * fifo_vals['unit_cost']
        }
        if quantity < 0.0:
            values.update({
                'remaining_qty': values['quantity'],
                'remaining_value': values['value']
            })
        return values

    def _ordered_lots(self):
        lot_ids = []
        for move_line in self:
            lot_id = move_line.lot_id.id
            if lot_id not in lot_ids:
                lot_ids += [lot_id]
        return lot_ids
