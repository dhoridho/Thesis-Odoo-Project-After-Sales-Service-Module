# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_purchase_configuration_limit = fields.Integer(
        string="Purchase configuration limit", default=5)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_purchase_configuration_limit = fields.Integer(
        related='company_id.sh_purchase_configuration_limit', readonly=False
    )
