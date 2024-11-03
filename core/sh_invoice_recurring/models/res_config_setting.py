# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_invoice_online_signature = fields.Boolean(
        'Invoice Recurring Online Signature')


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_invoice_online_signature = fields.Boolean(
        'Invoice Recurring Online Signature', related='company_id.sh_invoice_online_signature', readonly=False)
