from odoo import api, fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    preferred_location = fields.Many2one('stock.location', string='Preferred location')