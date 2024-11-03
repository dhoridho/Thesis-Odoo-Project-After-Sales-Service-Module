from odoo import api, fields, models


class ProductMining(models.Model):
    _name = 'product.mining.site'
    _description = 'Product Mining'

    mining_site_control_id = fields.Many2one(comodel_name='mining.site.control', string='Mining Site Control')
    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', domain="[('id', 'in', 'mining_site_control_id.operation_ids')]")
    product_id = fields.Many2many(comodel_name='product.product', string='Products')
