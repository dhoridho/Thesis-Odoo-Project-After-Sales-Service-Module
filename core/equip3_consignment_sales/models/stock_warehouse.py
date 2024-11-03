from odoo import _, api, fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_consignment_warehouse = fields.Boolean("Is Consignment Warehouse")
