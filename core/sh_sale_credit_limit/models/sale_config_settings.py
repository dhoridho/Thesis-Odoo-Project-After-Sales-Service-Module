# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_credit_limit_email_alerts = fields.Selection([('no_alerts', 'No Alerts'), ('all_approval', 'To All Approval'), ('by_team', 'By Team (Sales Channels)'), ('specific_users', 'Specific User')],
                                                      default='no_alerts', string="Email Alert For Sale Order Credit Limit")
    sale_email_specific_user_id = fields.Many2one(
        "res.users", "Email Alert User")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_credit_limit_email_alerts = fields.Selection(
        string="Email Alert For Sale Order Credit Limit", related="company_id.sale_credit_limit_email_alerts", readonly=False)
    sale_email_specific_user_id = fields.Many2one(
        "res.users", "Email Alert User", related="company_id.sale_email_specific_user_id", readonly=False)
