# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import string
import time
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WizardMPPromotion(models.TransientModel):
    _inherit = 'wiz.mp.promotion'

    _SP_PROMOTION_TYPE = [
        ('all', 'All'),
        ('discount', 'Product Discount'),
        ('voucher', 'Voucher'),
        ('bundle', 'Bundle Deal'),
        ('addon', 'Add on Deal')
    ]

    sp_promotion_type = fields.Selection(selection=_SP_PROMOTION_TYPE, string='Shopee Promotion Type', default='all')

    def shopee_get_promotion(self, **kwargs):
        kwargs.update({'promotion_type': self.sp_promotion_type})
        if hasattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace):
            getattr(self.mp_account_id, '%s_get_promotion' % self.mp_account_id.marketplace)(**kwargs)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
