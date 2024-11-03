
from odoo import models, fields, api, _


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    move_location_id = fields.Many2one(
        'stock.location', string='Move Location')
    package_measure_selection = fields.Selection([
        ('weight', 'Weight'),
        ('length', 'Length'),
        ('width', 'Width'),
        ('height', 'Height'),
        ('volume', 'Volume'),
    ], string="Package Measured By", readonly=True)

    package_weight = fields.Float(
        string='Package Weight', compute='_compute_package_weight', store=True)

    length = fields.Float(string="Length", readonly=True)
    maximum_length = fields.Float(
        string="Max Length", related="packaging_id.maximum_length", readonly=True)

    width = fields.Float(string="Width", readonly=True)
    maximum_width = fields.Float(
        string="Max Width", related="packaging_id.maximum_width", readonly=True)

    height = fields.Float(string="Height", readonly=True)
    maximum_height = fields.Float(
        string="Max Height", related="packaging_id.maximum_height", readonly=True)

    volume = fields.Float(string="Volume", readonly=True)
    maximum_volume = fields.Float(
        string="Max Volume", related="packaging_id.maximum_volume", readonly=True)

    @api.depends('quant_ids', 'quant_ids.product_id', 'quant_ids.quantity')
    def _compute_package_weight(self):
        for record in self:
            package_weight = 0
            for quant in record.quant_ids:
                package_weight += (quant.quantity * quant.product_id.weight)
            record.package_weight = package_weight
