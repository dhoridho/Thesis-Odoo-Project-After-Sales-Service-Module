from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    reception_steps = fields.Selection(selection="get_reception_steps_values", default='one_step', required=True,
                                       help="Default incoming route to follow")
    delivery_steps = fields.Selection(selection="get_delivery_steps_values", default='ship_only', required=True,
                                      help="Default outgoing route to follow")

    def get_reception_steps_values(self):
        configuration = self.env['ir.config_parameter'].sudo(
        ).get_param('is_warehouse_shipments')
        if not configuration:
            return [('one_step', 'Receive goods directly (1 step)')]
        else:
            return [
                ('one_step', 'Receive goods directly (1 step)'),
                ('two_steps', 'Receive goods in input and then stock (2 steps)'),
                ('three_steps', 'Receive goods in input, then quality and then stock (3 steps)')]

    def get_delivery_steps_values(self):
        configuration = self.env['ir.config_parameter'].sudo(
        ).get_param('is_warehouse_shipments')
        if not configuration:
            return [('ship_only', 'Deliver goods directly (1 step)')]
        else:
            return [
                ('ship_only', 'Deliver goods directly (1 step)'),
                ('pick_ship', 'Send goods in output and then deliver (2 steps)'),
                ('pick_pack_ship', 'Pack goods, send goods in output and then deliver (3 steps)')]
