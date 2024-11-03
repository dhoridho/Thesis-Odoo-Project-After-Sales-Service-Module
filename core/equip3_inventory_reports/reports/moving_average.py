from odoo import _, api, fields, models
from collections import defaultdict
from odoo.tools.float_utils import float_compare
from odoo.tools import float_round


class MovingAverage(models.Model):
    _name = 'moving.average'
    _description = 'Moving Average'

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse')
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    date = fields.Date(string='date')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM')
    average_cost = fields.Float(string='Average Cost')

    @api.model
    def _get_quant(self):
        domain = [('location_id', '!=', False), ('warehouse_id', '!=', False)]
        field = ['product_id', 'warehouse_id', 'quantity', 'value']
        groupby = ['warehouse_id', 'product_id']
        quants = self.env['stock.quant'].read_group(domain, field, groupby, lazy=False)

        current_date = fields.Date.context_today(self)
        moving_average_data = []

        data = defaultdict(lambda: {'quantity': 0, 'value': 0})
        for quant in quants:
            product_id = quant['product_id'][0]
            warehouse_id = quant.get('warehouse_id')[0]
            quantity = quant.get('quantity', 0)
            value = quant.get('value', 0)

            key = (warehouse_id, product_id)
            data[key]['quantity'] += quantity
            data[key]['value'] += value

        vals_list = []
        for (warehouse_id, product_id), values in data.items():
            total_quantity = values['quantity']
            value = values['value']

            value_per_quantity = value / total_quantity if total_quantity != 0 else 0
            value_per_quantity = float_round(value_per_quantity, precision_digits=2)

            existing_average_cost = self.env['moving.average'].search([
                ('product_id', '=', product_id),
                ('warehouse_id', '=', warehouse_id),
                ('date', '<', current_date),
            ]).mapped('average_cost')

            last_average_cost = next((x for x in reversed(existing_average_cost) if x != 0), None)
            if last_average_cost is not None and float_compare(value_per_quantity, last_average_cost, precision_digits=2) == 0:
                value_per_quantity = 0

            vals = {
                'create_uid': self.env.user.id,
                'write_uid': self.env.user.id,
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'average_cost': value_per_quantity,
                'date': current_date,
                'uom_id': self.env['product.product'].browse(product_id).uom_id.id
            }
            vals_list.append(vals)

        if vals_list:
            self.env['moving.average'].create(vals_list)
