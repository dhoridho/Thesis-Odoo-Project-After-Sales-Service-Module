# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import string
import time
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WizardMPPromotion(models.TransientModel):
    _inherit = 'wiz.mp.promotion'

    def tiktok_get_promotion(self, **kwargs):
        if hasattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
