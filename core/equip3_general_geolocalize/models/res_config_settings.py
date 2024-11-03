# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    geolocalize = fields.Boolean(string="Geo Localization", default=True)

    def set_values(self):
        res = super().set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_general_geolocalize.geolocalize', self.geolocalize)
        if not self.geolocalize:
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.geo_provider', False)
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.google_map_api_key', False)
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.geoloc_provider_techname', False)
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.geoloc_provider_googlemap_key', False)
        return res

    def get_values(self):
        res = super().get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        geolocalize = False
        if IrConfigParam.get_param('base_geolocalize.geo_provider'):
            geolocalize = True
        res.update({
            'geolocalize': geolocalize,
            # 'geoloc_provider_id': IrConfigParam.get_param('geoloc_provider_id', False),
            # 'geoloc_provider_techname': IrConfigParam.get_param('geoloc_provider_techname', False),
            # 'geoloc_provider_googlemap_key': IrConfigParam.get_param('geoloc_provider_googlemap_key', False),
        })
        return res