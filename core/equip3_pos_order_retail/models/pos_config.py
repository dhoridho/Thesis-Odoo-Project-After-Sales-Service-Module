# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class POSConfig(models.Model):
    _inherit = "pos.config"

    is_complementary = fields.Boolean(string="Complementary")
    required_ask_seat = fields.Boolean(string="Auto Ask Seat Number when add new product", default=False)
    table_reservation_list = fields.Boolean(string="Table Reservation List", default=False)