# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoice(self, order, so_line, amount):
        invoice_id = super(SaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        invoice_id.write({
            'apply_manual_currency_exchange': order.apply_manual_currency_exchange,
            'manual_currency_exchange_rate': order.manual_currency_exchange_rate
        })
        return invoice_id
