# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_order_information_in_message = fields.Boolean(
        "Order Information in message?", default=True)
    purchase_product_detail_in_message = fields.Boolean(
        "Order Product details in messsage?", default=True)
    purchase_signature = fields.Boolean("Signature?", default=True)
    purchase_display_in_message = fields.Boolean(
        "Display in Chatter Message?", default=True)
    po_send_pdf_in_message = fields.Boolean(
        "Send Report URL in message?", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_order_information_in_message = fields.Boolean(
        related="company_id.purchase_order_information_in_message", string="Order Information in message?", readonly=False)
    purchase_product_detail_in_message = fields.Boolean(
        related="company_id.purchase_product_detail_in_message", string="Order Product details in messsage?", readonly=False)
    purchase_signature = fields.Boolean(
        related="company_id.purchase_signature", string="Signature?", readonly=False)
    purchase_display_in_message = fields.Boolean(
        related="company_id.purchase_display_in_message", string="Display in Chatter Message?", readonly=False)
    po_send_pdf_in_message = fields.Boolean(
        related="company_id.po_send_pdf_in_message", string="Send Report URL in message?", readonly=False)
