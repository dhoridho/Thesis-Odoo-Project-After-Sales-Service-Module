# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountBankStatementLabel(models.Model):
    _name = 'account.bank.statement.label'
    _description = 'Account Bank Statement Label'

    name = fields.Char(string='Label Keyword')
    statement_label_id = fields.Many2one('mp.wallet.statement.label')
    action_type = fields.Selection([
        ('reconcile', 'Reconcile With Invoice'),
        ('manual', 'Manual Operations')], string='Action Type', required=True)
    account_id = fields.Many2one('account.account', string='Account')