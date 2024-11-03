# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    down_payment_product_id = fields.Many2one(
        'product.product',
        string='Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='tis_venue_booking.down_payment_product_id',
        help='Default product used for payment advances')

    venue_product_id = fields.Many2one(
        'product.product', string='Venue Product',
        domain="[('type', '=', 'service')]",
        config_parameter='tis_venue_booking.venue_product_id',
    )
    amenities_product_id = fields.Many2one(
        'product.product', string="Amenities Product",
        domain="[('type', '=', 'service')]",
        config_parameter='tis_venue_booking.amenities_product_id',
    )
    additional_charge_product_id = fields.Many2one(
        'product.product', string='Additional Charge Product',
        domain="[('type', '=', 'service')]",
        config_parameter='tis_venue_booking.additional_charge_product_id',
    )
    google_maps_view_api_key = fields.Char(string='Google Maps View Api Key')
    google_maps_theme = fields.Selection(
        selection=[('default', 'Default'),
                   ('aubergine', 'Aubergine'),
                   ('night', 'Night'),
                   ('dark', 'Dark'),
                   ('retro', 'Retro'),
                   ('silver', 'Silver')],
        string='Map theme')
    google_maps_places = fields.Boolean(string='Places', default=True)
    google_maps_geometry = fields.Boolean(string='Geometry', default=True)
    # start_time = fields.Float(string="Start Time")
    # end_time = fields.Float(string="End Time")
    # activate_day = fields.Boolean(string="Activate",default=False)


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        lib_places = self._set_google_maps_places()
        lib_geometry = self._set_google_maps_geometry()

        active_libraries = '%s,%s' % (lib_geometry, lib_places)

        ICPSudo.set_param('google.api_key_geocode',
                          self.google_maps_view_api_key)
        ICPSudo.set_param('google.maps_theme', self.google_maps_theme)
        ICPSudo.set_param('google.maps_libraries', active_libraries)
        # ICPSudo.set_param('tis_venue_booking.start_time', self.start_time)
        # ICPSudo.set_param('tis_venue_booking.end_time', self.end_time)
        # ICPSudo.set_param('tis_venue_booking.activate_day', self.activate_day)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()


        lib_places = self._get_google_maps_places()
        lib_geometry = self._get_google_maps_geometry()

        res.update({
            'google_maps_view_api_key': ICPSudo.get_param(
                'google.api_key_geocode', default=''),
            'google_maps_theme': ICPSudo.get_param(
                'google.maps_theme', default='default'),
            'google_maps_places': lib_places,
            'google_maps_geometry': lib_geometry,
            # 'start_time': ICPSudo.get_param('tis_venue_booking.start_time'),
            # 'end_time': ICPSudo.get_param('tis_venue_booking.end_time'),
            # 'activate_day':ICPSudo.get_param('tis_venue_booking.activate_day'),
        })
        return res

    @api.model
    def _get_google_maps_geometry(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'google.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'geometry' in libraries

    def _set_google_maps_geometry(self):
        return 'geometry' if self.google_maps_geometry else ''

    @api.model
    def _get_google_maps_places(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        google_maps_libraries = ICPSudo.get_param(
            'google.maps_libraries', default='')
        libraries = google_maps_libraries.split(',')
        return 'places' in libraries

    def _set_google_maps_places(self):
        return 'places' if self.google_maps_places else ''
