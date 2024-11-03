from odoo import models, fields


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_it_inventory_warehouse = fields.Boolean('IT Inventory Warehouse')
