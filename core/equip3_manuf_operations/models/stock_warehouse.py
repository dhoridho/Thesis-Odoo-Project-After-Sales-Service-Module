from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_sequence_values(self):
        values = super(StockWarehouse, self)._get_sequence_values()
        values['manu_type_id']['prefix'] = 'POR/%(y)s/%(month)s/%(day)s/'
        values['manu_type_id']['padding'] = 3
        values['manu_type_id']['use_date_range'] = True
        return values
