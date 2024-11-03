from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    filter_value_ids = fields.Many2many('product.attribute.value')
    measure_ids = fields.Many2many(
        'measure.for.packaging', string="Package Measure By")
    volume_calculation = fields.Boolean(string="Volume Calculation")
    volume_formula = fields.Char(string="Volume Calculation Formula")

    @api.onchange('volume_calculation', 'volume_formula', 'maximum_height', 'maximum_width', 'maximum_length')
    def _calculate_expression(self):
        for record in self:
            if record.volume_calculation == True:
                record.maximum_volume = int(
                    record.maximum_height) * int(record.maximum_width) * int(record.maximum_length)

    @api.constrains('product_id', 'measure_ids')
    def _check_product_measure(self):
        for record in self:
            product_names = ', '.join(product.display_name for product in record.product_id)
            measures = record.measure_ids

            if not measures:
                raise ValidationError(_('Product %s Missing Package Measure By Value', product_names))

            for measure in record.measure_ids:
                if measure.measure == 'volume':
                    if measure.maximum_height == 0.0:
                        raise ValidationError(_('Product %s Missing Maximum Height Value', product_names))
                    if measure.maximum_length == 0.0:
                        raise ValidationError(_('Product %s Missing Maximum length Value', product_names))
                    if measure.maximum_width == 0.0:
                        raise ValidationError(_('Product %s Missing Maximum Width Value', product_names))
                elif measure.measure == 'weight':
                    if record.max_weight == 0.0:
                        raise ValidationError(_('Product %s Missing Maximum Weight Value', product_names))

    @api.onchange('product_id', 'measure_ids')
    def _onchange_measure_by_package(self):
        for prod in self.product_id:
            for meas in self.measure_ids:
                if meas.measure == 'weight':
                    if prod.product_tmpl_id.weight <= 0:
                        raise ValidationError(_('Product %s Missing Weight Value in Master Data', prod.product_tmpl_id.name))
                if meas.measure == 'volume':
                    if prod.product_tmpl_id.width <= 0:
                        raise ValidationError(_('Product %s Missing Width Value in Master Data', prod.product_tmpl_id.name))
                    if prod.product_tmpl_id.length <= 0:
                        raise ValidationError(_('Product %s Missing Length Value in Master Data', prod.product_tmpl_id.name))
                    if prod.product_tmpl_id.height <= 0:
                        raise ValidationError(_('Product %s Missing Height Value in Master Data', prod.product_tmpl_id.name))
