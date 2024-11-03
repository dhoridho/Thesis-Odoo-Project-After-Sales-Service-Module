from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductRatioLine(models.Model):
    _name = 'product.ratio.line'
    _description = 'Product Ratio Line'

    @api.depends('uom_id', 'ratio', 'uom_ref_id')
    def _compute_description(self):
        for record in self:
            record.description = _('1 %s Equals to %s %s' % (
                record.uom_id.display_name,
                record.ratio,
                record.uom_ref_id.display_name
            ) if record.uom_id and record.uom_ref_id else False)

    @api.depends('uom_id')
    def _compute_uom_reference(self):
        UoM = self.env['uom.uom']
        for record in self:
            record.uom_ref_id = UoM.search([
                ('category_id', '=', record.uom_id and record.uom_id.category_id.id or False),
                ('uom_type', '=', 'reference')
            ], limit=1).id

    active = fields.Boolean()
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UOM', ondelete='cascade', required=True)
    product_id = fields.Many2one(comodel_name='product.product', string='Variant', domain="[('id', 'in', product_variant_ids)]")
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Product', required=True)
    description = fields.Char(string='Description', compute=_compute_description)
    ratio = fields.Float(string='Ratio', required=True, digits='Product Unit of Measure')
    uom_ref_id = fields.Many2one(comodel_name='uom.uom', string='UOM Reference Number', compute=_compute_uom_reference)

    # technical fields
    product_variant_ids = fields.One2many('product.product', related='product_tmpl_id.product_variant_ids')
    is_custom_uom = fields.Boolean(related='uom_id.is_custom_uom', readonly=False) # To force active Custom UoM when created from product form

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        if 'default_is_custom_uom' in self.env.context:
            self.is_custom_uom = self.env.context.get('default_is_custom_uom', False)

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        # need to reset variant when product change
        self.product_id = False

    @api.constrains('ratio')
    def _check_null_ratio(self):
        for record in self:
            if record.ratio <= 0.0:
                raise ValidationError(_('Ratio must be positive!'))

    @api.constrains('uom_id', 'product_id', 'product_tmpl_id')
    def _product_constrains(self):
        for record in self:
            product_id = record.product_id
            product_tmpl_id = record.product_tmpl_id
            if product_id and product_id not in product_tmpl_id.product_variant_ids:
                raise ValidationError(_('Invalid product variant!'))

            lines = self.search([
                ('uom_id', '=', record.uom_id.id),
                ('product_tmpl_id', '=', product_tmpl_id.id)
            ])
            if record not in lines:
                lines |= record
            product_ids = lines.mapped('product_id')

            if (product_ids and len(lines) != len(product_ids)) or (not product_ids and len(lines) > 1):
                raise ValidationError(_('Custom UoM with product and variant already created!'))
