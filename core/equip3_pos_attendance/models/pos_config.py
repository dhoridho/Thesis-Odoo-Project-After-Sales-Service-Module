# -*- coding: utf-8 -*-

from odoo import fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    pos_login_face_recognition = fields.Boolean('Face Recognition')
    integrate_with_hr = fields.Boolean("Integrate with HR", default=False)
    is_auto_sync_coupon = fields.Boolean()
