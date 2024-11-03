# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    hospitalization_usage_location = fields.Many2one('stock.location', 
        string='Hospitalization Usage Location for Consumed Products')
    hospitalization_stock_location = fields.Many2one('stock.location', 
        string='Hospitalization Stock Location for Consumed Products')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hospitalization_usage_location = fields.Many2one('stock.location', 
        related='company_id.hospitalization_usage_location',
        domain=[('usage','=','customer')],
        string='Hospitalization Usage Location for Consumed Products', 
        ondelete='cascade', help='Usage Location for Consumed Products', readonly=False)
    hospitalization_stock_location = fields.Many2one('stock.location', 
        related='company_id.hospitalization_stock_location',
        domain=[('usage','=','internal')],
        string='Hospitalization Stock Location for Consumed Products', 
        ondelete='cascade', help='Stock Location for Consumed Products', readonly=False)