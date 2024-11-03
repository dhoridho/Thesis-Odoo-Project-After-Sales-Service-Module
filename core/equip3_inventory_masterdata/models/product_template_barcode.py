
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductTemplateBarcode(models.Model):
    _inherit = 'product.template.barcode'

    product_uom_id = fields.Many2one('uom.uom')
    product_uom_category_id = fields.Many2one('uom.category', related='product_uom_id.category_id', store=True)
    uom_id = fields.Many2one('uom.uom', string='UOM', domain="[('category_id', '=', product_uom_category_id)]")


    
    @api.model
    def default_get(self, fields):
        res = super(ProductTemplateBarcode, self).default_get(fields)
        
        product_template_id =  self.env.context.get('product_tmpl_id')
        if product_template_id:
            product = self.env['product.product'].search([('product_tmpl_id', '=', product_template_id)], limit=1)
            
            if product:
                res['product_id'] = product.id
        
        return res