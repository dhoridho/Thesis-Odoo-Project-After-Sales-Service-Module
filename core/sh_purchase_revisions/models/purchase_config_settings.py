# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_purchase_revision = fields.Boolean("Enable Purchase Revisions")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_purchase_revision = fields.Boolean("Enable Purchase Revisions", related="company_id.sh_purchase_revision", readonly=False)
