# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountInvoice(models.Model):
#    _inherit = "account.invoice"
    _inherit = "account.move"

    related_project_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account"
    )
