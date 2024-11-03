# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class res_company(models.Model):
    _inherit = "res.company"

    sh_it_barcode_mobile_type = fields.Selection([
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('sh_qr_code', 'QR code'),
        ('all', 'All')
    ], default='barcode', string='Product Scan Options In Mobile (Internal Transfer)',)

    sh_it_bm_is_cont_scan = fields.Boolean(
        string='Continuously Scan? (Internal Transfer)')

    sh_it_bm_is_notify_on_success = fields.Boolean(
        string='Notification On Product Succeed? (Internal Transfer)')

    sh_it_bm_is_notify_on_fail = fields.Boolean(
        string='Notification On Product Failed? (Internal Transfer)')

    sh_it_bm_is_sound_on_success = fields.Boolean(
        string='Play Sound On Product Succeed? (Internal Transfer)')

    sh_it_bm_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Product Failed? (Internal Transfer)')

    sh_it_bm_is_add_product = fields.Boolean(
        string="Is add new product in picking? (Internal Transfer)")
