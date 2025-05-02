from odoo import models, fields, api
from odoo.tools.translate import html_translate
from lxml import html

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_warranty = fields.Boolean(string='Has Warranty')
    warranty_period_id = fields.Many2one('warranty.period', string='Warranty Period')
    website_description = fields.Html('Description for the website', sanitize_attributes=False, translate=html_translate, sanitize_form=False)

    def action_update_warranty_description(self):
        for product in self:
            name = ''
            desc = ''
            if product.warranty_period_id:
                name = product.warranty_period_id.name or ''
            desc = product.description or ''
            description_html = f"<p><strong>Warranty Coverage:</strong> {name}</p> <p>{desc}</p>"
            product.website_description = description_html

    @api.onchange('warranty_period_id', 'description')
    def _onchange_for_website_description(self):
        for record in self:
            record.action_update_warranty_description()

    @api.onchange('has_warranty')
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
    warranty_period_id = fields.Many2one('warranty.period', string='Warranty Period')

    @api.onchange('has_warranty')
    def _onchange_product_has_warranty(self):
        if not self.has_warranty:
            self.warranty_period_id = False

    def write(self, vals):
        if 'has_warranty' in vals and not vals.get('has_warranty'):
            vals['warranty_period_id'] = False
        return super(Product, self).write(vals)
