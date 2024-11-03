# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_gift_product = fields.Boolean('Is Gift Product') 


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_gift_product = fields.Boolean('Is Gift Product', related='product_tmpl_id.is_gift_product') 

    def pos_product_domain(self):
        res = super(ProductProduct, self).pos_product_domain()
        res = res and res or []
        domain = [('gift_reward_id','!=',False), ('product_id','!=',False)]
        gift_products = self.env['pos.loyalty.reward.product'].search_read(domain, ['product_id'])
        if gift_products:
            res = ['|', '|', ('is_gift_product','=',True), ('id','in', [x['product_id'][0] for x in gift_products]) ] + res
        else:
            res = ['|', ('is_gift_product','=',True)] + res
        return res