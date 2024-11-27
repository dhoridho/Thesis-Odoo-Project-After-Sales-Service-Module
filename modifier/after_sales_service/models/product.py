from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_warranty = fields.Boolean(string='Has Warranty')
    warranty_period_id = fields.Many2one('warranty.period', string='Warranty Period', required=True)

    @api.onchange('is_material')
    def _onchange_product_has_warranty(self):
        if not self.has_warranty:
            self.warranty_period_id = False

    def write(self, vals):
        if 'has_warranty' in vals and not vals.get('has_warranty'):
            vals['warranty_period_id'] = False
        return super(ProductTemplate, self).write(vals)

class Product(models.Model):
    _inherit = 'product.product'

    has_warranty = fields.Boolean(string='Has Warranty')
    warranty_period_id = fields.Many2one('warranty.period', string='Warranty Period', required=True)

    @api.onchange('is_material')
    def _onchange_product_has_warranty(self):
        if not self.has_warranty:
            self.warranty_period_id = False

    def write(self, vals):
        if 'has_warranty' in vals and not vals.get('has_warranty'):
            vals['warranty_period_id'] = False
        return super(ProductTemplate, self).write(vals)
