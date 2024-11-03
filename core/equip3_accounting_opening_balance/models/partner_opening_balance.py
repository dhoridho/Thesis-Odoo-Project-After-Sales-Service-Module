# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PartnerOpeningBalance(models.Model):
    _name = "partner.opening.balance"

    partner_id = fields.Many2one('res.partner', string='Partner Name')
    account_receivable_id = fields.Many2one('account.account', string='Account Receivable')
    account_payable_id = fields.Many2one('account.account', string='Account Payable')
    payable_opening_balance_ids = fields.One2many('payable.opening.balance', 'partner_opening_bal_id', string="Payable opening balance")
    receivable_opening_balance_ids = fields.One2many('receivable.opening.balance', 'partner_opening_bal_id', string="Receivable opening balance")

class PayableOpeningBalance(models.Model):
    _name = "payable.opening.balance"

    partner_opening_bal_id = fields.Many2one('partner.opening.balance', string='Partner Opening Balance Id')
    vendor_id = fields.Many2one('res.partner', string='Vendor Name')
    invoice = fields.Char(string='Invoice')
    date = fields.Date(string='Date')
    description = fields.Char(string='Description')
    due_date = fields.Date(string='Due Date')
    amount_due = fields.Float(string='Amount Due')

class ReceivableOpeningBalance(models.Model):
    _name = "receivable.opening.balance"

    partner_opening_bal_id = fields.Many2one('partner.opening.balance', string='Partner Opening Balance Id')
    customer_id = fields.Many2one('res.partner', string='Customer Name')
    purchase_order = fields.Char(string='Purchase Order')
    date = fields.Date(string='Date')
    description = fields.Char(string='Description')
    due_date = fields.Date(string='Due Date')
    amount_due = fields.Float(string='Amount Due')