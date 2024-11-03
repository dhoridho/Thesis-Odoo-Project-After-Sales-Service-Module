# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'
# group_sale_layout this group remove
#     @api.model
#     def get_values(self):
#         res = super(ResConfigSettings, self).get_values()
#         ICPSudo = self.env['ir.config_parameter'].sudo()
#         res.update(
#             group_sale_layout=ICPSudo.get_param('sale.group_sale_layout'),
#         )
#         return res

#     def set_values(self):
#         super(ResConfigSettings, self).set_values()
#         ICPSudo = self.env['ir.config_parameter'].sudo()
#         ICPSudo.set_param("sale.group_sale_layout", self.group_sale_layout)
