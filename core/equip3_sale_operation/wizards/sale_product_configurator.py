from odoo import models,fields


class SaleProductConfiguratorInherit(models.TransientModel):
    _inherit = 'sale.product.configurator'

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    is_single_warehouse = fields.Boolean(string='Is Single Warehouse',)
    
    
    
    