from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    tag_ids = fields.Many2one('stock.location.tag', string='Tags')
    quantity_validate = fields.Boolean(compute='compute_quantity_validate')

    @api.depends('capacity_unit')
    def compute_quantity_validate(self):
        self.quantity_validate = False
        # if self.capacity_unit < self.occupied_unit:
        #     raise ValidationError("The quantity max should be greater than occupied quantity ")

    @api.onchange('capacity_unit')
    def validation_if_occupied_exceeds_100(self):
        if self.capacity_unit < self.occupied_unit:
            raise ValidationError("The quantity max should be greater than occupied quantity ")

