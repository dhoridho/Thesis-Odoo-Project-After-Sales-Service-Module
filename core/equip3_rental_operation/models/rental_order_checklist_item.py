
from odoo import api , fields , models


class RentalOrderChecklistItem(models.Model):
    _name = "rental.order.checklist.item"
    _description = "Rental Order Checklist Item"

    name = fields.Char(string="Name")
    price = fields.Float(string="Price")