from odoo import models, fields
from odoo.tools import float_round


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    analytic_group = fields.Many2many(related='production_id.analytic_tag_ids')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mrp_workorder_id', string='Valuations', readonly=True)

    def _byproduct_update(self, line):
        values = super(MrpWorkorder, self)._byproduct_update(line)
        production = self.production_id
        allocated_cost = (self.qty_remaining / production.product_qty) * line['allocated_cost']
        values.update({
            'allocated_cost': allocated_cost,
        })
        return values

    def _finished_update(self, line):
        values = super(MrpWorkorder, self)._finished_update(line)
        production = self.production_id
        values.update({
            'allocated_cost': (self.qty_remaining / production.product_qty) * line['allocated_cost']
        })
        return values
