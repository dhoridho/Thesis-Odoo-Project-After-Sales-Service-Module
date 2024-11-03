from odoo import _, api, fields, models



class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_out_svl_vals(self, quantity, company):
        self.ensure_one()
        stock_valuation_layer_vals = super(ProductProduct, self)._prepare_out_svl_vals(quantity, company)
        move_line = self.ensure_context('_prepare_out_svl_vals', 'move')
        valued_move_lines = move_line._get_valued_move_lines()
        stock_move = valued_move_lines.move_id
        sale_order_line = stock_move.sale_line_id

        def update_bundle_proportion_cost(data, unit_cost, quantity):
            data['unit_cost'] = unit_cost
            data['value'] = -abs(unit_cost * quantity) if data['value'] < 0 else abs(unit_cost * quantity)

        if sale_order_line.product_id.is_pack:
            unit_cost = stock_move.price_unit
            update_bundle_proportion_cost(stock_valuation_layer_vals, unit_cost, quantity)

            for line_entry in stock_valuation_layer_vals['line_ids']:
                line_data = line_entry[2]
                update_bundle_proportion_cost(line_data, unit_cost, line_data['quantity'])

        return stock_valuation_layer_vals