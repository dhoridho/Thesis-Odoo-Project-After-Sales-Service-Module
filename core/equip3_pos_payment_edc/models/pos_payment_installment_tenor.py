# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosPaymentInstallmentTenor(models.Model):
    _name = 'pos.payment.installment.tenor'
    _description = 'Pos Payment Installment Tenor'

    name = fields.Char('Name')
    value = fields.Selection([
        ('01', '1 month'),
        ('03', '3 months'),
        ('06', '6 months'),
        ('12', '12 months'),
        ('24', '24 months')
    ], string='Value')