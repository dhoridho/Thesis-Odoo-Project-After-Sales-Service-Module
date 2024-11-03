# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = "res.company"

    sh_sale_barcode_mobile_type = fields.Selection([
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('sh_qr_code', 'QR code'),
        ('all', 'All')
    ], default='all', string='Product Scan Options In Mobile (Sale)',)