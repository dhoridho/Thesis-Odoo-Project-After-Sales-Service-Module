# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _inherit = 'mp.token'

    tts_user_type = fields.Char(string="Tiktok User Type", readonly=True)
    tts_open_id = fields.Char(string="Tiktok Open ID", readonly=True)
    tts_auth_code = fields.Char(string="Tiktok Auth Code", readonly=True)

    @api.model
    def tiktok_create_token(self, mp_account, raw_token):
        mp_token_obj = self.env['mp.token']

        expired_date = datetime.now() + relativedelta(seconds=raw_token.get('access_token_expire_in'))
        values = {
            'name': raw_token.get('access_token'),
            'expired_date': fields.Datetime.to_string(expired_date),
            'mp_account_id': mp_account.id,
            'tts_user_type': raw_token.get('user_type'),
            'tts_open_id': raw_token.get('open_id'),
            'tts_auth_code': raw_token.get('auth_code'),
            'raw': self.format_raw_data(raw_token)
        }
        mp_token_obj.create(values)

    # @api.multi
    def tiktok_validate_current_token(self):
        self.ensure_one()
        if self.state != 'valid':
            self.mp_account_id.action_authenticate()
            return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
        return self
