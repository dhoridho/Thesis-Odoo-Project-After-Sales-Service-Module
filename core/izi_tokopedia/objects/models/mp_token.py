# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MarketplaceToken(models.Model):
    _inherit = 'mp.token'

    tp_token_type = fields.Char(string="Tokopedia Token Type", readonly=True)

    @api.model
    def tokopedia_create_token(self, mp_account, raw_token):
        mp_token_obj = self.env['mp.token']

        expired_date = datetime.now() + relativedelta(seconds=raw_token.get('expires_in'))
        values = {
            'name': raw_token.get('access_token'),
            'expired_date': fields.Datetime.to_string(expired_date),
            'mp_account_id': mp_account.id,
            'tp_token_type': raw_token.get('token_type'),
            'raw': self.format_raw_data(raw_token)
        }
        mp_token_obj.create(values)

    # @api.multi
    def tokopedia_validate_current_token(self):
        self.ensure_one()
        if self.state != 'valid':
            # self.mp_account_id.action_authenticate()
            try:
                token = self.mp_account_id.tokopedia_authenticate()
                if token:
                    return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
            except Exception as e:
                time_now = str((datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"))
                auth_message = "%s from: %s" % (str(e.args[0]), time_now)
                self.mp_account_id.write({'state': 'authenticating', 'auth_message': auth_message})
                return self.mp_account_id.mp_token_ids.sorted('expired_date', reverse=True)[0]
        return self
