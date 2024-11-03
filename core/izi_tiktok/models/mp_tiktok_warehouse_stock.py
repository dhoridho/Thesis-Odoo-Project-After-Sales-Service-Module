from odoo import models, fields, api

class MPTiktokWarehouseStock(models.Model):
    _name = 'mp.tiktok.warehouse.stock'

    name = fields.Char(string='Label dari Field')
    tts_var_stock = fields.Integer(string='Stock')
    mp_product_variant_id = fields.Many2one(
        comodel_name='mp.product.variant',
        string='Product',
        ondelete='cascade'
        )
    warehouse_id = fields.Many2one('mp.tiktok.warehouse', string='Warehouse', ondelete='cascade')
