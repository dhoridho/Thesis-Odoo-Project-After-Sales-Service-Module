from odoo import models, fields, api


class MrpFlexibleConsumptionWarning(models.TransientModel):
    _name = 'mrp.flexible.consumption.warning'
    _description = 'MRP Flexible Consumption Warning'

    consumption_id = fields.Many2one('mrp.consumption', string='Consumption', required=True)
    material_ids = fields.One2many('mrp.flexible.consumption.warning.line', 'warning_material_id', string='Materials', readonly=True)
    byproduct_ids = fields.One2many('mrp.flexible.consumption.warning.line', 'warning_byproduct_id', string='ByProducts', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        return self.consumption_id.with_context(consumption_confirmed=True).button_confirm()


class MrpFlexibleConsumptionWarningLine(models.TransientModel):
    _name = 'mrp.flexible.consumption.warning.line'
    _description = 'MRP Flexible Consumption Warning Line'

    warning_material_id = fields.Many2one('mrp.flexible.consumption.warning', string='Warning Material')
    warning_byproduct_id = fields.Many2one('mrp.flexible.consumption.warning', string='Warning Byproduct')

    product_id = fields.Many2one('product.product', string='Product')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    expected_qty = fields.Float(digits='Product Unit of Measure', string='Expected Quantity')
    actual_qty = fields.Float(digits='Product Unit of Measure', string='Actual Quantity')
