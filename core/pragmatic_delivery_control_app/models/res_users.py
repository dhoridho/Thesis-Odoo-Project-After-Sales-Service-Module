# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', help="The warehouse in which user belongs to.")
    
