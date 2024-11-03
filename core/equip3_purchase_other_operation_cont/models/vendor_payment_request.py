# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class VendorPaymentRequestLine(models.Model):
    _inherit = 'vendor.payment.request.line'

    purchase_order_id = fields.Many2one(domain="[('state', '=', 'purchase'), ('dp', '=', False)]")
