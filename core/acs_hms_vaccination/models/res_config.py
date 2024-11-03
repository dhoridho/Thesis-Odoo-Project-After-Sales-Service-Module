# -*- coding: utf-8 -*-
# Part of AlmightyCS See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    vaccination_invoicing = fields.Boolean("Allow Vaccination Invoicing", default=True)
    vaccination_usage_location = fields.Many2one('stock.location', 
        string='Usage Location for Consumed Vaccine.')
    vaccination_stock_location = fields.Many2one('stock.location', 
        string='Stock Location for Consumed Vaccine')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vaccination_invoicing = fields.Boolean("Allow Vaccination Invoicing", related='company_id.vaccination_invoicing', readonly=False)
    vaccination_usage_location = fields.Many2one('stock.location', 
        related='company_id.vaccination_usage_location',
        domain=[('usage','=','customer')],
        string='Usage Location for Consumed Vaccine', readonly=False)
    vaccination_stock_location = fields.Many2one('stock.location', 
        related='company_id.vaccination_stock_location',
        domain=[('usage','=','internal')],
        string='Stock Location for Consumed vaccination_usage_location', readonly=False)