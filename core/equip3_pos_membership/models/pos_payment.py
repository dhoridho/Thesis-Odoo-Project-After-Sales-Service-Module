# -*- coding: utf-8 -*-

from odoo import models, fields


class PosPayment(models.Model):
    _inherit = 'pos.payment'
     
    customer_deposit_id = fields.Many2one('customer.deposit', 'Customer Deposit')


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'
 
    is_deposit_payment = fields.Boolean('Is Deposit Payment', 
        help='Payment with Member Deposit/Customer Deposit')