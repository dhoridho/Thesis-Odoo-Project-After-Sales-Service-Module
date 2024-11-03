# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    quot_to_po = fields.Boolean(string="Quotation to Purchase Order")
    so_to_po = fields.Boolean(string="Sale Order to Purchase Order")


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    quot_to_po = fields.Boolean(string="Quotation to Purchase Order",
                                related="company_id.quot_to_po",
                                readonly=False)
    so_to_po = fields.Boolean(string="Sale Order to Purchase Order",
                              related="company_id.so_to_po",
                              readonly=False)
