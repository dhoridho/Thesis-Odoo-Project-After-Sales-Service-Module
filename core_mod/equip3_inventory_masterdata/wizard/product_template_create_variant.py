from odoo import fields, models, api


class ProductTemplateCreateVariant(models.TransientModel):
    _name = "product.template.create.variant"
    _description = "Product Template Create Variant"

    variant_ids = fields.One2many('product.template.create.variant.line', 'variant_id', string='Variants')

    def create_variants(self):
        context = dict(self.env.context) or {}
        product = self.env['product.template'].browse([context.get('active_id')])
        variant = []
        attribute_ids = product.attribute_line_ids.mapped('attribute_id').ids
        for variant_id in self.variant_ids:
            if variant_id.attribute_id.id not in attribute_ids:
                variant.append((0, 0, {
                    'attribute_id': variant_id.attribute_id.id, 
                    'value_ids': [(6, 0, variant_id.value_ids.ids)],
                }))
            else:
                attribute_line = product.attribute_line_ids.filtered(lambda r: r.attribute_id.id == variant_id.attribute_id.id)
                if attribute_line:
                    variant.append((1, attribute_line.id, {
                        'value_ids': [(4, value) for value in variant_id.value_ids.ids],
                    }))
        product.attribute_line_ids = variant


class ProductTemplateCreateVariantLine(models.TransientModel):
    _name = "product.template.create.variant.line"
    _description = 'Product Template Create Variant'

    variant_id = fields.Many2one('product.template.create.variant', string="Variant")
    attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='restrict', required=True, index=True)
    value_ids = fields.Many2many('product.attribute.value', 'product_attribute_value_variant_rel', 'attribute_id', 'value_id',  string="Values")
    filter_value_ids = fields.Many2many('product.attribute.value', compute='_compute_value_ids', store=False)

    @api.depends('attribute_id', 'value_ids')
    def _compute_value_ids(self):
        context = dict(self.env.context) or {}
        product = self.env['product.template'].browse([context.get('active_id')])
        for record in self:
            record.filter_value_ids = [(6, 0, product.variant_attribute_value_ids.attribute_value_ids.mapped('product_attribute_value_id').ids)]
