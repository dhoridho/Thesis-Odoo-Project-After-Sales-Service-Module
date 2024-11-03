from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    mining_economic_product = fields.Selection(selection=[
        ('economic', 'Economic'),
        ('non-economic', 'Non-Economic')
    ], string='Economic Product')
