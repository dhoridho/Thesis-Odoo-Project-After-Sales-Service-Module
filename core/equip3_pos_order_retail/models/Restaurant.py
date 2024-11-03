# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    customer_name = fields.Char(string="Customer")
    date_reserve = fields.Datetime(string="Date Reserve")
    tbl_moved_from = fields.Many2one('restaurant.table',string="Moved from")
    clear_interval = fields.Char(string="Clear Interval")