from odoo import api, models, fields, _


class DeliveryBoyTracking(models.Model):
    _name = "delivery.boy.tracking"
    _description = 'Delivery Boy Tracking'
    _rec_name = "delivery_boy_id"

    delivery_boy_id = fields.Many2one("res.partner",string="Delivery Boy")
    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")
