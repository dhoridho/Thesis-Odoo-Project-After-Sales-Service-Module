# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import string
import time
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WizardMPPromotion(models.TransientModel):
    _inherit = 'wiz.mp.promotion'

    _TP_PROMOTION_TYPE = [
        ('all', 'All'),
        ('discount', 'Slash Price'),
        ('bundle', 'Bundle Discount'),
    ]

    tp_promotion_type = fields.Selection(selection=_TP_PROMOTION_TYPE, string='Tokopedia Promotion Type', default='all')

    def tokopedia_get_promotion(self, **kwargs):
        kwargs.update({'promotion_type': self.sp_promotion_type})
        if hasattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
