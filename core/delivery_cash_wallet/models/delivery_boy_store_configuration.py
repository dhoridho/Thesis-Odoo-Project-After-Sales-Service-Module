from odoo import api, models, fields, _


class DeliveryBoyStore(models.Model):
    _name = "delivery.boy.store"
    _description = 'Delivery Boy Store'
    _rec_name = "delivery_boy_id"

    location_id = fields.Many2one("stock.location", string="Store/Location")
    delivery_boy_id = fields.Many2one("res.users",string="Delivery Boys",
                                       domain=lambda self: [('partner_id.is_driver', '=', True)])
    is_auto_create = fields.Boolean(string="Auto Create",default=False)
