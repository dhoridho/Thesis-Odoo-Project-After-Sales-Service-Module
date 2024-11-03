# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import timeit
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    mp_invoice_number = fields.Char(string='MP Invoice Number', index=True)
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='MP Account')


    def action_post(self):
        timer = timeit.default_timer() # CHECK_DURATION
        res = super(AccountMove, self).action_post()
        # _logger.info('CHECK_DURATION > Post Invoice %s' % ((timeit.default_timer() - timer)))
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    mp_invoice_number = fields.Char(related='move_id.mp_invoice_number', store=True, string='MP Invoice Number', index=True)
    mp_account_id = fields.Many2one(related='move_id.mp_account_id', comodel_name='mp.account', string='MP Account')
