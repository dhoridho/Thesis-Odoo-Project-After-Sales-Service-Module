from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    location_ids = fields.Many2many('stock.location',string="Location")

class picking_order(models.Model):
    _inherit = "picking.order"

