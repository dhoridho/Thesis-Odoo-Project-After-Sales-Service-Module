from odoo import fields, models, api


class ProductTemplateVariantMarketplace(models.TransientModel):
    _name = "product.template.variant.marketplace"
    _description = "Product Template Variant Marketplace"

    mp_variant_ids = fields.One2many('product.template.variant.marketplace.line', 'mp_variant_id', string='Variants')

    def create_variants(self):
        context = dict(self.env.context) or {}
        product = self.env['product.template'].browse([context.get('active_id')])
        variant = []
        attribute_ids = product.attribute_line_ids.mapped('attribute_id').ids
        for variant_id in self.mp_variant_ids:
            if variant_id.mp_attribute_id.id not in attribute_ids:
                variant.append((0, 0, {
                    'attribute_id': variant_id.mp_attribute_id.id,
                    'value_ids': [(6, 0, variant_id.mp_value_ids.ids)],
                }))
            else:
                attribute_line = product.attribute_line_ids.filtered(lambda r: r.attribute_id.id == variant_id.mp_attribute_id.id)
                if attribute_line:
                    variant.append((1, attribute_line.id, {
                        'value_ids': [(4, value) for value in variant_id.mp_value_ids.ids],
                    }))
        product.attribute_line_ids = variant


class ProductTemplateVariantMarketplaceLine(models.TransientModel):
    _name = "product.template.variant.marketplace.line"
    _description = 'Product Template Variant Marketplace Line'

    mp_variant_id = fields.Many2one('product.template.variant.marketplace', string="Variant")
    mp_attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='restrict', required=True, index=True)
    mp_unit_id = fields.Many2one('product.attribute.unit', string="Attribute Unit", required=False,
                                      index=True)
    mp_value_ids = fields.Many2many('product.attribute.value', 'product_attribute_value_variant_marketplace', 'attribute_id', 'value_id',  string="Values")
    mp_filter_value_ids = fields.Many2many('product.attribute.value', compute='_compute_value_ids', store=False)

    @api.depends('mp_attribute_id', 'mp_value_ids')
    def _compute_value_ids(self):
        context = dict(self.env.context) or {}
        product = self.env['product.template'].browse([context.get('active_id')])
        for record in self:
            record.mp_filter_value_ids = [(6, 0, product.mp_attribute_value_ids.attribute_value_ids.mapped('product_attribute_value_id').ids)]
