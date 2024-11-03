# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    maint_request_custom_id = fields.Many2one(
    	'maintenance.request',
    	string='Maintenance Request',
    	readonly=True,
    	copy=False,
    )