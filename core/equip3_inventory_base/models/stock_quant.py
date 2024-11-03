from odoo import models, fields, api, _
from odoo.tools import float_is_zero


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse')

    # technical_fields
    to_assign_in_date = fields.Boolean()

    @api.depends('location_id')
    def _compute_warehouse(self):
        for quant in self:
            quant.warehouse_id = quant.location_id.get_warehouse().id

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity', 'lot_id', 'warehouse_id')
    def _compute_value(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        svl_vals_list = []
        for quant in self:
            quant.currency_id = quant.company_id.currency_id
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            
            product_contexed = quant.product_id.with_context(lot_id=quant.lot_id.id)
            if is_cost_per_warehouse:
                product_contexed = product_contexed.with_context(price_for_warehouse=quant.warehouse_id.id, price_for_location=quant.location_id.id)
            
            quantity = product_contexed.quantity_svl
            if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                quant.value = 0.0
                continue
            average_cost = product_contexed.value_svl / quantity
            quant.value = quant.quantity * average_cost
