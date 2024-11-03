from odoo import api, fields, models, _
from odoo.tools import float_is_zero


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_product_service_operation = fields.Boolean(string="Product Service Operation")



class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _run_fifo_init_line_values(self):
        res = super(ProductProduct, self)._run_fifo_init_line_values()
        res.update({'svl_source_id': False})
        return res

    @api.model
    def _run_fifo_update_line_values(self, **kwargs):
        res = super(ProductProduct, self)._run_fifo_update_line_values(**kwargs)
        candidate = kwargs.get('candidate', self.env['stock.valuation.layer.line'])
        source = candidate._source()
        res.update({
            'svl_source_line_id': source.id,
            'svl_source_id': source.svl_id.id
        })
        return res

    @api.model
    def _run_fifo_parameters(self):
        return super(ProductProduct, self)._run_fifo_parameters() + ['candidate']
    
    @api.model
    def _run_standard_init_line_values(self):
        return {}

    @api.model
    def _run_standard_update_line_values(self, **kwargs):
        candidate = kwargs.get('candidate', self.env['stock.valuation.layer.line'])
        source = candidate._source()
        return {
            'svl_source_line_id': source.id,
            'svl_source_id': source.svl_id.id
        }

    @api.model
    def _run_standard_parameters(self):
        return ['lot_value', 'candidate']

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        res = super(ProductProduct, self)._prepare_in_svl_vals(quantity, unit_cost)
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        move = self.ensure_context('_prepare_in_svl_vals', 'move')
        if move._is_in_and_out():
            cost_method = self.cost_method
            product = move.product_id
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=move.location_dest_id.get_warehouse().id)

            total_qty = 0.0
            total_value = 0.0

            cost_method = move.product_id.with_company(move.company_id).cost_method
            standard_price_unit = 0.0
            if cost_method == 'standard':
                standard_price_unit = product.standard_price

            line_values = []
            for svl_line in move.stock_valuation_layer_ids.line_ids:
                if cost_method == 'standard':
                    line_unit_cost = standard_price_unit
                else:
                    line_unit_cost = svl_line.unit_cost
                
                line_qty = abs(svl_line.quantity)
                line_value = line_unit_cost * line_qty
                source = svl_line._source()

                values = {
                    'stock_move_line_id': svl_line.stock_move_line_id.id,
                    'svl_source_line_id': source.id,
                    'svl_source_id': source.svl_id.id,
                    'lot_id': svl_line.lot_id.id,
                    'quantity': line_qty,
                    'unit_cost': line_unit_cost,
                    'value': line_value
                }
                if cost_method in ('average', 'fifo'):
                    values.update({
                        'remaining_qty': line_qty,
                        'remaining_value': line_value
                    })
                
                line_values += [(0, 0, values)]
                total_qty += line_qty
                total_value += line_value

            if cost_method == 'standard':
                svl_unit_cost = standard_price_unit
            else:
                svl_unit_cost = 0.0
                if not float_is_zero(total_qty, precision_rounding=self.uom_id.rounding):
                    svl_unit_cost = total_value / total_qty

            res.update({
                'unit_cost': svl_unit_cost,
                'value': svl_unit_cost * res.get('quantity', 0.0),
                'line_ids': line_values
            })
        return res

    def _prepare_out_svl_vals(self, quantity, company):
        res = super(ProductProduct, self)._prepare_out_svl_vals(quantity, company)
        move = self.ensure_context('_prepare_out_svl_vals', 'move')

        if self.cost_method == 'standard':
            standard_values = self._run_standard(quantity, company)

            if not move.inventory_id:
                lot_values = standard_values['lot_values']
                remaining_qty = standard_values['remaining_qty']
                
                res.update({'standard_remaining_qty': remaining_qty})

                for line_vals in res.get('line_ids', []):
                    lot_id = line_vals[-1]['lot_id']
                    lot_value = lot_values[lot_id]
                    lot_remaining_qty = lot_value.get('remaining_qty', 0.0)
                    line_vals[-1].update({
                        'standard_remaining_qty': lot_remaining_qty,
                        'svl_source_id': lot_value.get('svl_source_id', False)
                    })

        if self.env.context.get('empty_stock', False):
            for line_vals in res.get('line_ids', []):
                mark_id = int(self.env['ir.sequence'].next_by_code('svl.line.mark.id'))
                line_vals[-1].update({'mark_id': mark_id})
        return res
        
    def _run_standard(self, quantity, company, svl=None):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        move = self.ensure_context('_run_standard', 'move')
        lot_ids = move._ordered_lots()
        lines = move._get_lot_move_lines_dict()
        line_model = 'stock.move.line' if move._name == 'stock.move' else 'tmp.stock.move.line'
        warehouse_id = self.env.context.get('price_for_warehouse', False)

        domain = [
            ('product_id', '=', self.id),
            ('standard_remaining_qty', '>', 0),
            ('company_id', '=', company.id),
            ('lot_id', 'in', lot_ids)
        ]

        if svl:
            domain += [('create_date', '<', svl.create_date)]

        if is_cost_per_warehouse:
            domain += [('warehouse_id', '=', warehouse_id)]

        qty_to_take_on_candidates = abs(quantity)
        qty_to_take_on_lots = {lot_id: sum(ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
            for ml in self.env[line_model].browse(lines[lot_id])) for lot_id in lot_ids}

        candidates = self.env['stock.valuation.layer.line'].browse()
        lot_values = {lot_id: self._run_standard_init_line_values() for lot_id in lot_ids}
        for candidate in self.env['stock.valuation.layer.line'].sudo().search(domain):
            qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.standard_remaining_qty)
            candidate.write({
                'standard_remaining_qty': candidate.standard_remaining_qty - qty_taken_on_candidate,
            })
            candidate.svl_id.write({
                'standard_remaining_qty': candidate.svl_id.standard_remaining_qty - qty_taken_on_candidate,
            })
            candidates |= candidate

            lot_value = lot_values[candidate.lot_id.id]
            update_params = {}
            for v in self._run_standard_parameters():
                update_params[v] = eval(v)
            lot_value.update(self._run_standard_update_line_values(**update_params))

            qty_to_take_on_candidates -= qty_taken_on_candidate
            qty_to_take_on_lots[candidate.lot_id.id] -= qty_taken_on_candidate

            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                break
        
        remaining_qty = 0.0
        if qty_to_take_on_candidates > 0.0:
            remaining_qty = -qty_to_take_on_candidates
            for lot_id in lot_ids:
                lot_values[lot_id]['remaining_qty'] = -qty_to_take_on_lots[lot_id]

        return {
            'candidates': candidates,
            'remaining_qty': remaining_qty,
            'lot_values': lot_values
        }

    def _run_fifo(self, quantity, company):
        self = self.with_context(run_fifo_executed=True)
        res = super(ProductProduct, self)._run_fifo(quantity, company)
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        if is_cost_per_warehouse and self.cost_method == 'fifo':
            move = self.ensure_context('_run_fifo', 'move')
            if move._is_in_and_out():
                product_contexed = self.with_context(price_for_warehouse=move.location_dest_id.get_warehouse().id)
                dest_warehouse_qty = product_contexed.quantity_svl
                if float_is_zero(dest_warehouse_qty, precision_rounding=self.uom_id.rounding):
                    if 'source_line_values' in res:
                        first_fifo_price = res['source_line_values'][0].get('unit_cost', 0.0)
                    else:
                        first_fifo_price = res.get('unit_cost', 0.0)
                    product_contexed.with_context(disable_auto_svl=True).standard_price = first_fifo_price
        self = self.with_context(run_fifo_executed=False)
        return res

    @api.model
    def _svl_empty_stock_am(self, stock_valuation_layers):
        move_vals_list = super(ProductProduct, self)._svl_empty_stock_am(stock_valuation_layers)
        branch = self.env.branch
        for move_vals in move_vals_list:
            move_vals = self.env['account.move']._query_complete_account_move_fields(move_vals, branch)
        return move_vals_list

    @api.model
    def _svl_replenish_stock_am(self, stock_valuation_layers):
        move_vals_list = super(ProductProduct, self)._svl_replenish_stock_am(stock_valuation_layers)
        branch = self.env.branch
        for move_vals in move_vals_list:
            move_vals = self.env['account.move']._query_complete_account_move_fields(move_vals, branch)
        return move_vals_list

    @api.model
    def _svl_empty_stock(self, description, product_category=None, product_template=None):
        self = self.with_context(empty_stock=True)
        return super(ProductProduct, self)._svl_empty_stock(description, product_category=product_category, product_template=product_template)

    @api.model
    def _svl_replenish_stock_prepare_tmp_move_lines(self, svl_line_values):
        res = super(ProductProduct, self)._svl_replenish_stock_prepare_tmp_move_lines(svl_line_values)
        svl_source_line_id = self.env['stock.valuation.layer.line'].search([
            ('mark_id', '=', svl_line_values['mark_id'])
        ], limit=1, order='id desc')._source().id

        res.update({
            'price_unit': svl_line_values['unit_cost'],
            'svl_source_line_id': svl_source_line_id
        })
        return res
