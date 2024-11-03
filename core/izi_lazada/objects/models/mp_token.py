# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class MarketplaceToken(models.Model):
    _inherit = 'mp.token'

    lz_email_account = fields.Char(string='LZ Email Account')
    lz_country_user_ids = fields.One2many('mp.lazada.country.user', 'mp_token_id', string='Lazada Country Users')

    @api.model
    def lazada_create_token(self, mp_account, raw_token):
        mp_token_obj = self.env['mp.token']

        expired_date = datetime.now() + relativedelta(seconds=raw_token.get('expires_in'))
        values = {
            'name': raw_token.get('access_token'),
            'expired_date': fields.Datetime.to_string(expired_date),
            'mp_account_id': mp_account.id,
            'refresh_token': raw_token.get('refresh_token'),
            'lz_email_account': raw_token.get('account', None),
            'raw': self.format_raw_data(raw_token)
        }
        token = mp_token_obj.create(values)
        return token

    def lazada_validate_current_token(self):
        self.ensure_one()
        if self.state != 'valid':
            token = self.mp_account_id.lazada_renew_token()
            if token:
                return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
        return self
