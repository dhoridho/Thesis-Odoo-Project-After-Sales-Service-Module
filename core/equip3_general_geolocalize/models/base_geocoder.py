# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

class GeoCoder(models.AbstractModel):
    _inherit = "base.geocoder"

    # @api.model
    # def _get_provider(self):
    #     res = super()._get_provider()
    #     geolocalize = self.env['ir.config_parameter'].sudo().get_param('equip3_general_geolocalize.geolocalize')
    #     if not geolocalize:
    #         return False
    #     return res


    @api.model
    def _get_provider(self):
        res = super(GeoCoder, self)._get_provider()
        geolocalize = self.env['ir.config_parameter'].sudo().get_param('equip3_general_geolocalize.geolocalize')
        if not geolocalize:
            return res
        return res
