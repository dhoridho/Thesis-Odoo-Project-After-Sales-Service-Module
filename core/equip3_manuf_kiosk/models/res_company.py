# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    manuf_kiosk_barcode_mobile_type = fields.Selection([
        ('lot_sn', 'Lots/Serial numbers'),
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('qr_code', 'QR code'),
        ('all', 'All')
    ], default='barcode', string='Product Scan Options In Mobile (KIOSK)', translate=True)

    manuf_kiosk_bm_is_cont_scan = fields.Boolean(string='Barcode Continuously Scan? (KIOSK)', default='False')

    manuf_kiosk_bm_is_notify_on_success = fields.Boolean(
        string='Notification On Product Succeed? (KIOSK)', default='False')

    manuf_kiosk_bm_is_notify_on_fail = fields.Boolean(
        string='Notification On Product Failed? (KIOSK)', default='False')

    manuf_kiosk_bm_is_sound_on_success = fields.Boolean(
        string='Play Sound On Product Succeed? (KIOSK)', default='False')

    manuf_kiosk_bm_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Product Failed? (KIOSK)', default='False')
    
    # cofig for employee scan
    manuf_kiosk_att_is_cont_scan = fields.Boolean(string='Employee Continuously Scan? (KIOSK)', default='False')

    manuf_kiosk_att_is_notify_on_success = fields.Boolean(
        string='Notification On Attendance Succeed (KIOSK)', default='False')

    manuf_kiosk_att_is_notify_on_fail = fields.Boolean(
        string='Notification On Attendance Failed? (KIOSK)', default='False')

    manuf_kiosk_att_is_sound_on_success = fields.Boolean(
        string='Play Sound On Attendance Succeed? (KIOSK)', default='False')

    manuf_kiosk_att_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Attendance Failed? (KIOSK)', default='False')