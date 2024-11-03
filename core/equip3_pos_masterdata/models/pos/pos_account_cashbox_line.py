# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PosAccountCashboxLine(models.Model):
    """ Cash Box Details """
    _name = 'pos.account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'coin_value'
    _order = 'coin_value'

    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        for cashbox_line in self:
            cashbox_line.subtotal = cashbox_line.coin_value * cashbox_line.number

    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='#Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    pos_config_id = fields.Many2one('pos.config', string="POS Config")


class AccountCashboxLine(models.Model):
    _inherit = "account.cashbox.line"

    pos_config_id = fields.Many2one('pos.config', string="POS Config")
    pos_session_id = fields.Many2one('pos.session', string="POS Session")
    is_closing_line = fields.Boolean("Closing balance wizard lines")