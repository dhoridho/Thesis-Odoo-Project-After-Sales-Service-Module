
from odoo import api , fields , models, _
import ast

class ProductTemplateIn(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        if 'categ_product_reward_id' in context:
            vals['categ_id'] = context.get('categ_product_reward_id')
        res = super(ProductTemplateIn, self).create(vals)
        return res