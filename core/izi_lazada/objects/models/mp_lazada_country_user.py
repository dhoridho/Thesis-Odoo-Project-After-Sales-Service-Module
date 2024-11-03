# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah


from odoo import api, fields, models


class MPLazadaCountryUser(models.Model):
    _name = 'mp.lazada.country.user'
    _inherit = 'mp.base'
    _rec_name = 'user_id'

    user_id = fields.Char(string='Lazada User ID')
    seller_id = fields.Char(string='Lazada User ID')
    country = fields.Char(string='Lazada User ID')
    short_code = fields.Char(string='Lazada User ID')
    mp_token_id = fields.Many2one(comodel_name='mp.token', string='MP Token')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'user_id': ('user_id', None),
            'mp_external_id': ('user_id', None),
            'seller_id': ('seller_id', None),
            'country': ('country', None),
            'short_code': ('short_code', None),
            'mp_token_id': ('mp_token_id', None)
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPLazadaCountryUser, cls)._add_rec_mp_field_mapping(mp_field_mappings)
