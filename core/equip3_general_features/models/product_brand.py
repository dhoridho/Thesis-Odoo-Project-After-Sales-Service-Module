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
        products = self.env['product.template'].search([('product_brand_id','=', self.id)])
        self.product_count = len(products)

    @api.constrains('brand_name')
    def _product_category_check(self):
        prod_brand = self.env['product.brand'].search([])
        if prod_brand:
            for brand in prod_brand:
                if (brand.brand_name == self.brand_name) and (brand.id != self.id):
                    raise ValidationError("The Brand name %s already exists."
                                          " Please create new one with another Brand Name" % self.brand_name )

    def get_products_in_brand_method(self):
        products = self.env['product.template'].search([('product_brand_id','=', self.id)])
        action = self.env.ref('product.product_template_action_all').read()[0]
        domain = [('id', 'in', products.ids)]
        action['context'] = {'search_default_product_brand_id': 1}
        action['domain'] = domain
        return action
