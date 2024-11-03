# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class InventorySettings(models.TransientModel):

    _inherit = 'res.config.settings'

    inv_cost = fields.Boolean(string="Inventory Adjustments with Cost",default=False,
        related="company_id.inv_cost" ,readonly=False)

    def set_values(self):
        super(InventorySettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('bi_inventory_adjustment_with_cost.inv_cost', self.inv_cost)

    @api.model
    def get_values(self):
        res = super(InventorySettings, self).get_values()
        res.update({
            'inv_cost':bool(self.env['ir.config_parameter'].sudo().get_param('bi_inventory_adjustment_with_cost.inv_cost')),
            })
        return res
