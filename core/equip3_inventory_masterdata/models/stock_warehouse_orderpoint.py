from odoo import models, fields


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    action_to_take = fields.Selection([
        ('no_action', 'No Action'),
        ('create_pr', 'Create Purchase Request'),
        ('create_rfq', 'Create Request For Quotation'),
        ('create_itr', 'Create Internal Transfer Request'),
        ('create_mr', 'Create Material Request'),
    ], tracking=True, default='no_action')
