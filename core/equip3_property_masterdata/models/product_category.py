from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    stock_type = fields.Selection(selection_add=[('property', 'Property'),], ondelete={'property': 'cascade'})

    @api.model
    def create_property_category(self):
        product_category = self.env['product.category'].search([]).mapped('name')
        categ_name = [x.title() for x in product_category]
        if 'Property' not in categ_name:
            self.create({
                    'name': 'Property',
                    'stock_type': 'property',
                    'property_cost_method': 'standard',
                    'property_valuation': 'manual_periodic',
                    'category_prefix': 'PRT',
                    'current_sequence': '001',
                })
            