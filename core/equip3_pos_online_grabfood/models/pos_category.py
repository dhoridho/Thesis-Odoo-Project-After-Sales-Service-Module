# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosCategory(models.Model):
    _inherit = "pos.category"

    @api.model
    def create(self, values):
        res = super(PosCategory, self).create(values)
        if 'is_online_outlet' in values:
            self.env['pos.online.outlet'].grabfood_do_auto_update_menu()
        return res

    def write(self, vals):
        res = super(PosCategory, self).write(vals)
        if 'is_online_outlet' in vals:
            self.env['pos.online.outlet'].grabfood_do_auto_update_menu()
        return res