from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError


class UomUomInherit(models.Model):
    _inherit = 'uom.uom'
    _order = 'create_date desc'

    is_custom_uom = fields.Boolean(string='Custom Unit of Measure', default=False)
    product_ratio_line = fields.One2many(comodel_name='product.ratio.line', inverse_name='uom_id', string='Product Ratio Line')

    def _valid_field_parameter(self, field, name):
        return name == 'product_field' or super()._valid_field_parameter(field, name)

    def _factor(self, product):
        self.ensure_one()
        product = product or self.env.context.get('product_field', self.env['product.product'])
        if not self.is_custom_uom or not product:
            return self.factor

        if product._name == 'product.product':
            custom_uom = self.product_ratio_line.filtered(lambda line: line.product_id == product) # exact variant
            if not custom_uom:
                custom_uom = self.product_ratio_line.filtered(lambda line: line.product_tmpl_id == product.product_tmpl_id)
        else:
            custom_uom = self.product_ratio_line.filtered(lambda line: line.product_tmpl_id == product)

        return (1 / custom_uom.ratio) if custom_uom else self.factor

    def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True, product=False):
        if not self:
            return qty

        self.ensure_one()
        if (not self.is_custom_uom and not to_unit.is_custom_uom):
            return super(UomUomInherit, self)._compute_quantity(qty, to_unit, round=round, rounding_method=rounding_method, raise_if_failure=raise_if_failure)

        if self != to_unit and self.category_id.id != to_unit.category_id.id:
            if raise_if_failure:
                raise UserError(_('The unit of measure %s defined on the order line doesn\'t belong to the same category as the unit of measure %s defined on the product. Please correct the unit of measure defined on the order line or on the product, they should belong to the same category.') % (self.name, to_unit.name))
            else:
                return qty

        if self == to_unit:
            amount = qty
        else:
            product = product or self.env['product.product']
            src_factor = self._factor(product)
            amount = qty / src_factor
            if to_unit:
                dest_factor = to_unit._factor(product)
                amount = amount * dest_factor

        if to_unit and round:
            amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method='HALF-UP')
        return amount

    def _compute_price(self, price, to_unit, product=False):
        self.ensure_one()
        if (not self.is_custom_uom and not to_unit.is_custom_uom):
            return super(UomUomInherit, self)._compute_price(price, to_unit)

        if self != to_unit and self.category_id.id != to_unit.category_id.id:
            return price
        
        product = product or self.env['product.product']
        amount = price * self._factor(product)
        if to_unit:
            amount = amount / to_unit._factor(product)
        return amount

    @api.model
    def create(self, vals):
        uoms = super(UomUomInherit, self).create(vals)
        uoms.toggle_active_custom_uom()
        return uoms

    def write(self, vals):
        result = super(UomUomInherit, self).write(vals)
        self.toggle_active_custom_uom()
        return result

    def toggle_active_custom_uom(self):
        custom_uoms = self.filtered(lambda u: u.is_custom_uom)
        normal_uoms = self - custom_uoms
        custom_uoms.with_context(active_test=False).mapped('product_ratio_line').action_unarchive()
        normal_uoms.mapped('product_ratio_line').action_archive()
