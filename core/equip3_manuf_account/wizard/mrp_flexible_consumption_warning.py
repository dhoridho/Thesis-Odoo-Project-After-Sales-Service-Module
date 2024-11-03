from odoo import models, fields, api


class MrpFlexibleConsumptionWarningLine(models.TransientModel):
    _inherit = 'mrp.flexible.consumption.warning.line'

    expected_allocated_cost = fields.Float(digits='Product Unit of Measure', string='Expected Allocated Cost')
    actual_allocated_cost = fields.Float(digits='Product Unit of Measure', string='Actual Allocated Cost')
