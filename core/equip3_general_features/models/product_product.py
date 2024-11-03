
from re import findall as regex_findall
from re import split as regex_split
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_prefix = fields.Char(string="Product Code Prefix", size=10)
    is_generate_product = fields.Boolean(related='categ_id.is_generate_product_code')
    category_prefix_preference = fields.Selection(related='categ_id.category_prefix_preference')

    @api.model
    def create(self, vals):
        if vals.get('product_tmpl_id', False):
            template = self.env['product.template'].browse(vals['product_tmpl_id'])
            categ = template.categ_id
            if categ.is_generate_product_code:
                
                if 'default_code' not in vals:
                    default_code = template.default_code
                    if not default_code:
                        product_prefix = template.product_prefix
                        default_code = categ._next_sequence(product_prefix)
                    vals['default_code'] = default_code
                else:
                    default_code = vals['default_code']

                categ._check_and_update_next_sequence(default_code)
        
        return super(ProductProduct, self).create(vals)

