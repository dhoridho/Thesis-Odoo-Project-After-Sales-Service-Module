# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CrmSalespersonTracking(models.Model):
    _name = 'crm.salesperson.tracking'
    _description = 'CRM Salesperson Tracking'

    sales_person = fields.Many2one('res.users', string="Sales Person", required=True)
    current_datetime = fields.Datetime('Current Datetime')
    location_name = fields.Char(string="Location Name")
    latitude = fields.Char(string="Latitude")
    longitude = fields.Char(string="Longitude")
