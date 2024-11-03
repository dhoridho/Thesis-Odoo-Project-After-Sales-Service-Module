from odoo import api, models, fields, _


class DeliveryBoyStatus(models.Model):
    _name = "delivery.boy.status"
    _description = 'Delivery Boy Status'
    _rec_name = "driver_id"

    driver_id = fields.Many2one("res.users", string="Driver", domain=lambda self: [('partner_id.is_driver', '=', True)])
    state = fields.Selection([('online', 'Online'), ('offline', 'Offline')], string="Status")
