from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero, float_round


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_low_stock = fields.Boolean(string="Is Low Stock")
    
    # @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    # def _compute_value(self):
    #     """ For standard and AVCO valuation, compute the current accounting
    #     valuation of the quants by multiplying the quantity by
    #     the standard price. Instead for FIFO, use the quantity times the
    #     average cost (valuation layers are not manage by location so the
    #     average cost is the same for all location and the valuation field is
    #     a estimation more than a real value).
    #     """
    #     for quant in self:
    #         quant.currency_id = quant.company_id.currency_id
    #         # If the user didn't enter a location yet while enconding a quant.
    #         if not quant.location_id:
    #             quant.value = 0
    #             return

    #         if not quant.location_id._should_be_valued() or\
    #                 (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
    #             quant.value = 0
    #             continue
    #         if quant.product_id.cost_method == 'fifo':
    #             lot_id = quant.lot_id.id
    #             quantity = quant.product_id.with_context(lot_id=lot_id).quantity_svl
    #             if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
    #                 quant.value = 0.0
    #                 continue
    #             average_cost = quant.product_id.with_company(quant.company_id).with_context(lot_id=lot_id).value_svl / quantity
    #             quant.value = quant.quantity * average_cost
    #         else:
    #             quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).standard_price
