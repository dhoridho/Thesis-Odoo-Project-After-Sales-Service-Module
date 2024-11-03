# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResConfigSettingsKiosk(models.TransientModel):
    _inherit = 'res.config.settings'

    manuf_kiosk_barcode_mobile_type = fields.Selection(
        related='company_id.manuf_kiosk_barcode_mobile_type', string='Product Scan Options In Mobile (KIOSK)', translate=True, readonly=False)

    manuf_kiosk_bm_is_cont_scan = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_cont_scan', readonly=False)

    manuf_kiosk_bm_is_notify_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_notify_on_success', string='Notification On Product Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_notify_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_notify_on_fail', string='Notification On Product Failed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_sound_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_sound_on_success', string='Play Sound On Product Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_sound_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_sound_on_fail', string='Play Sound On Product Failed? (KIOSK)', readonly=False)
    
    # cofig for employee scan
    manuf_kiosk_att_is_cont_scan = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_cont_scan', readonly=False)

    manuf_kiosk_att_is_notify_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_notify_on_success', string='Notification On Attendance Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_notify_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_notify_on_fail', string='Notification On Attendance Failed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_sound_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_sound_on_success', string='Play Sound On Attendance Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_sound_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_sound_on_fail', string='Play Sound On Attendance Failed? (KIOSK)', readonly=False)
