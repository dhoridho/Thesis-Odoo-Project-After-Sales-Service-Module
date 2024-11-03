# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import time
import json
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

PARAMS = [
    ('by_default', 'With No MP Promotion ID'),
    ('by_mp_promotion_id', 'By MP Promotion ID'),
]


class WizMPPromotion(models.TransientModel):
    _name = 'wiz.mp.promotion'
    _description = 'MP Promotion Wizard'

    mp_account_id = fields.Many2one(comodel_name="mp.account", string="MP Account", required=True)
    marketplace = fields.Selection(related="mp_account_id.marketplace", string="Marketplace")
    mp_promotion_id = fields.Char(string="MP Promotion ID", required=False)
    params = fields.Selection(string="Parameter", selection=PARAMS, required=True, default="by_default")

    def get_promotion(self):
        kwargs = {'params': self.params,
                  'force_update': self._context.get('force_update', False)}
        if self.params == 'by_mp_promotion_id':
            kwargs.update({'mp_promotion_id': self.mp_promotion_id})
        if hasattr(self, '%s_get_promotion' % self.mp_account_id.marketplace):
            getattr(self, '%s_get_promotion' % self.mp_account_id.marketplace)(**kwargs)
