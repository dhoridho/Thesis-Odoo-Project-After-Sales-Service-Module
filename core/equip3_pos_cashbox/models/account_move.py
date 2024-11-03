# -*- coding: utf-8 -*-

from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_pos_cash_management = fields.Boolean('Is from POS Cash Management?')
    is_from_pos_cash_difference = fields.Boolean('Is from POS Cash Difference?')