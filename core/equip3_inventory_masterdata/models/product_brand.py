from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = 'brand_name'

    brand_name = fields.Char('Brand Name', tracking=True, required=True)
    short_name = fields.Char(string='Short Name')
    product_count = fields.Integer(
        '# Products', compute='_compute_product_count',
        help="The number of products under this brand")

    def _compute_product_count(self):
        for brand in self:
            brand.product_count = self.env['product.template'].search_count([('product_brand_ids','=', brand.id)])

    @api.model
    def create(self, vals):
        attribute = self.env['product.attribute'].search([('name','=','Brand')])
        if attribute:
            self.env['product.attribute.value'].create({
                'name': vals['brand_name'],
                'short_name': vals['short_name'],
                'attribute_id': attribute.id})
        else:
            product_attribute = self.env['product.attribute'].create({
                'name': "Brand"
            })
            self.env['product.attribute.value'].create({
                'name': vals['brand_name'],
                'short_name': vals['short_name'],
                'attribute_id': product_attribute.id})
        return super(ProductBrand, self).create(vals)

    @api.constrains('brand_name')
    def _product_category_check(self):
        prod_brand = self.env['product.brand'].search([('brand_name', '=', self.brand_name), ('id', '!=', self.id)], limit=1)
        if prod_brand:
            raise ValidationError("The Brand name %s already exists."
                                    " Please create new one with another Brand Name" % self.brand_name )

    def get_products_in_brand_method(self):
        products = self.env['product.template'].search([('product_brand_ids','=', self.id)])
        action = self.env.ref('product.product_template_action_all').read()[0]
        domain = [('id', 'in', products.ids)]
        action['context'] = {'search_default_product_brand_id': 1}
        action['domain'] = domain
        return action
