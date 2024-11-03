from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_promotion_product = fields.Boolean('Is Promotion Product')

    def unlink(self):
        for rec in self:
            if rec.is_promotion_product:
                raise ValidationError("You cannot delete promotional products")
        return super().unlink()

    def write(self, vals):
        for rec in self:
            if rec.is_promotion_product:
                if 'name' in vals:
                    vals['name'] = rec.name
        res = super().write(vals)
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_promotion_product = fields.Boolean('Is Promotion Product')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.is_promotion_product:
            if res.product_variant_id:
                res.product_variant_id.is_promotion_product = True
        return res

    def unlink(self):
        for rec in self:
            if rec.is_promotion_product:
                raise ValidationError("You cannot delete promotional products")
        return super().unlink()