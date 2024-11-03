# -*- coding: utf-8 -*-

from odoo import api, models, fields

class RestaurantPrinter(models.Model):
    _inherit = "restaurant.printer"

    printer_type = fields.Selection(selection_add=[
        ('network', 'Printer Network Address')
    ], ondelete={
        'network': 'set default',
    })
    printer_id = fields.Many2one('pos.epson', 'Epson Printer Network Device')

    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

