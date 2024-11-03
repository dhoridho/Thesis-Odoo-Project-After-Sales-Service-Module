# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    sh_invoice_recurring_order_id = fields.Many2one(
        "invoice.recurring", string="Recurring Order")
