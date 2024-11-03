# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MPWalletStamentLabel(models.Model):
    _name = 'mp.wallet.statement.label'
    _description = 'Marketplace Wallet Statement Label'

    name = fields.Char('Name')
    mp_account_ids = fields.Many2many('mp.account', string='Marketplace Accounts')
    invoice_number_keyword = fields.Char(string='Invoice Number Keyword')
    line_ids = fields.One2many('account.bank.statement.label', 'statement_label_id', 'Label Details')
    active = fields.Boolean('Active', default=True)
