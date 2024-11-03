# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    surgery_usage_location = fields.Many2one('stock.location', 
        string='Surgery Usage Location for Consumed Products')
    surgery_stock_location = fields.Many2one('stock.location', 
        string='Surgery Stock Location for Consumed Products')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    surgery_usage_location = fields.Many2one('stock.location', 
        related='company_id.surgery_usage_location',
        domain=[('usage','=','customer')],
        string='Surgery Usage Location for Consumed Products', 
        ondelete='cascade', help='Usage Location for Consumed Products in Surgery', readonly=False)
    surgery_stock_location = fields.Many2one('stock.location', 
        related='company_id.surgery_stock_location',
        domain=[('usage','=','internal')],
        string='Surgery Stock Location for Consumed Products', 
        ondelete='cascade', help='Stock Location for Consumed Products in Surgery', readonly=False)

    