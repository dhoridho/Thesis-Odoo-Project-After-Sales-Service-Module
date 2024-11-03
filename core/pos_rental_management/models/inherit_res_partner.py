# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models


class InheritAccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    prevent_partial_payment = fields.Boolean(
        string="Don't Allow Partial Payment In POS")


class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    prevent_partial_payment = fields.Boolean(
        related="property_payment_term_id.prevent_partial_payment", string="Don't allow partial payment in POS", readonly=False)
