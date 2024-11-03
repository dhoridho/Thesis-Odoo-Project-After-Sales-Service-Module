# -*- coding: utf-8 -*
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductPriceQuantity(models.Model):
    _name = "product.price.quantity"
    _description = "Sale price for each quantity"

    product_tmpl_id = fields.Many2one('product.template', 'Product Template', required=1)
    price_unit = fields.Float('Price', required=1, help='Price ally with quantity smaller than or equal this quantity')
    quantity = fields.Float('Qty', required=1, help='Quantity smaller than or equal, will apply price')


    @api.model
    def create(self, vals):
        if vals.get('price_unit') <= 0 or vals.get('quantity') <= 0:
            raise UserError(_('Price unit and quantity could not smaller than 0'))
        return super(ProductPriceQuantity, self).create(vals)

    def write(self, vals):
        if ((vals.get('price_unit', None) and vals.get('price_unit', None) <= 0) or vals.get('quantity', None) and vals.get('quantity', None) <= 0):
            raise UserError(_('Price unit and quantity could not smaller than 0'))
        return super(ProductPriceQuantity, self).create(vals)



class ProductUomPrice(models.Model):
    _name = "product.uom.price"
    _description = "Management product price each unit"

    uom_id = fields.Many2one('uom.uom', 'Uom', required=1) # v12 only
    product_tmpl_id = fields.Many2one('product.template', 'Product', domain=[('available_in_pos', '=', True)], required=1)

    @api.model
    def create(self, vals):
        product_template = self.env['product.template'].browse(vals.get('product_tmpl_id'))
        unit = self.env['uom.uom'].browse(vals.get('uom_id'))
        if product_template.uom_id and product_template.uom_id.category_id != unit.category_id:
            raise UserError('Please choose unit the same category of this product, for made linked stock inventory')
        return super(ProductUomPrice, self).create(vals)

    def write(self, vals):
        if vals.get('uom_id', None):
            unit_will_change = self.env['uom.uom'].browse(vals.get('uom_id'))
            for uom_price in self:
                if uom_price.product_tmpl_id.uom_id and uom_price.product_tmpl_id.uom_id.category_id != unit_will_change.category_id:
                    raise UserError(
                        'Please choose unit the same category of base product unit is %s, for made linked stock inventory' % uom_price.product_tmpl_id.uom_id.category_id.name)
        return super(ProductUomPrice, self).write(vals)
