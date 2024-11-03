# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    past_x_days_sales = fields.Integer("Use X days sales history in RFM Segmentation")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['past_x_days_sales'] = int(self.env['ir.config_parameter'].sudo().get_param('setu_rfm_analysis.past_x_days_sales', default=365))
        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('setu_rfm_analysis.past_x_days_sales', self.past_x_days_sales)
        return super(ResConfigSettings, self).set_values()
