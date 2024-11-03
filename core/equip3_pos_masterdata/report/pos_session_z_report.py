# -*- coding: utf-8 -*-

from odoo import fields, models, api, SUPERUSER_ID, _

class pos_session(models.Model):
    _inherit = "pos.session"
    
    def get_promotion_name(self, promotion_id):
        if promotion_id:
            promotion_name = self.env['pos.promotion'].browse([promotion_id]).name
            return promotion_name