from odoo import _, api, fields, models

class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_display_name = fields.Char(
        string='Location Display Name', compute='_compute_location_display_name', store=True)

    @api.depends('display_name')
    def _compute_location_display_name(self):
        for record in self:
            record.location_display_name = record.display_name
