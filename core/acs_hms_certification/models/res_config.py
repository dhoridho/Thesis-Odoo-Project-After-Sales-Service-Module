# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    acs_certificate_qrcode = fields.Boolean(string="Print Authetication QrCode on Certificate", default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acs_certificate_qrcode = fields.Boolean(related='company_id.acs_certificate_qrcode', string="Print Authetication QrCode on Certificate", readonly=False)
 