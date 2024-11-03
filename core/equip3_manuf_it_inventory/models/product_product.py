from odoo import models, fields, api
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # see _compute_quantities_dict on stock
    def _compute_quantities_dict_custom(self, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()

        domain_move_in = [('product_id', 'in', self.ids), ('state', '=', 'done')] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids), ('state', '=', 'done')] + domain_move_out_loc
        domain_move_in_past = domain_move_in[:]
        domain_move_out_past = domain_move_out[:]

        if from_date:
            date_date_expected_domain_from = [('date', '>=', from_date)]
            domain_move_in += date_date_expected_domain_from
            domain_move_out += date_date_expected_domain_from
            domain_move_in_past += [('date', '<', from_date)]
            domain_move_out_past += [('date', '<', from_date)]
        else:
            # to keep first balance 0.0
            domain_move_in_past += [('id', '=', False)]
            domain_move_out_past += [('id', '=', False)]

        if to_date:
            date_date_expected_domain_to = [('date', '<=', to_date)]
            domain_move_in += date_date_expected_domain_to
            domain_move_out += date_date_expected_domain_to

        Move = self.env['stock.move'].with_context(active_test=False)
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_past, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_past, ['product_id', 'product_qty'], ['product_id'], orderby='id'))

        res = dict()
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            if not product_id:
                res[product_id] = dict.fromkeys(['first_balance', 'income', 'outcome'], 0.0)
                continue
            rounding = product.uom_id.rounding
            res[product_id] = {}

            income = moves_in_res.get(product_id, 0.0)
            outcome = moves_out_res.get(product_id, 0.0)
            income_past = moves_in_res_past.get(product_id, 0.0)
            outcome_past = moves_out_res_past.get(product_id, 0.0)
            first_balance = max([income_past - outcome_past, 0.0])

            res[product_id]['first_balance'] = float_round(first_balance, precision_rounding=rounding)
            res[product_id]['income'] = float_round(income, precision_rounding=rounding)
            res[product_id]['outcome'] = float_round(outcome, precision_rounding=rounding)

        return res
