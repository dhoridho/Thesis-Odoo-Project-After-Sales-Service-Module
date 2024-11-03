from odoo import api, fields , models, _


class DeliveryTypeSale(models.Model):
    _name = 'delivery.type.sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Delivery Type Sale"
    _order = "name desc"

    name = fields.Char('Name')
    active = fields.Boolean('Active')
