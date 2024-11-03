# -*- coding: utf-8 -*-

from odoo import models, fields

class RestaurantPrinter(models.Model):
    _inherit = 'restaurant.printer'

    printer_type = fields.Selection(selection_add=[('bluetooth_printer', 'Use an EasyERPS App Service')])
    EasyERPS_app_port = fields.Char(string='EasyERPS Printer App Service Port', help="App Port.")
    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        help='Only Branch Assigned can use this printer'
    )