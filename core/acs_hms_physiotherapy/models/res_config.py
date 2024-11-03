# -*- coding: utf-8 -*-
# Part of AlmightyCS See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    physiotherapy_anytime_invoice = fields.Boolean("Allow Invoice Anytime in Physiotherapy")
    physiotherapy_invoice_advance = fields.Boolean("Invoice before Accepting in Physiotherapy")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    physiotherapy_anytime_invoice = fields.Boolean("Allow Invoice Anytime in Physiotherapy", related='company_id.physiotherapy_anytime_invoice', readonly=False)
    physiotherapy_invoice_advance = fields.Boolean("Invoice before Accepting in Physiotherapy", related='company_id.physiotherapy_invoice_advance', readonly=False)

    @api.onchange('physiotherapy_anytime_invoice')
    def onchnage_physiotherapy_anytime_invoice(self):
        if self.physiotherapy_anytime_invoice:
            self.physiotherapy_invoice_advance = False

    @api.onchange('physiotherapy_invoice_advance')
    def onchnage_physiotherapy_invoice_advance(self):
        if self.physiotherapy_invoice_advance:
            self.physiotherapy_anytime_invoice = False