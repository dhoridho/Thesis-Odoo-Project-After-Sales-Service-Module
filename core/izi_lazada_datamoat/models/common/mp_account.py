# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from odoo.exceptions import UserError

from odoo import api, fields, models


class MarketplaceAccount(models.Model):
    _inherit = 'mp.account'

    lz_datamoat_active = fields.Boolean(string="Lazada Datamoat Active", compute="_compute_lz_datamoat")
    lz_datamoat_show_toggle = fields.Boolean(string="Lazada Datamoat Show Toggle", compute="_compute_lz_datamoat")

    def _compute_lz_datamoat(self):
        icp_sudo = self.env['ir.config_parameter'].sudo()
        self.lz_datamoat_active = self.lz_app_key == icp_sudo.get_param('lazop.app_key')
        self.lz_datamoat_show_toggle = all([self.marketplace == 'lazada', self.state == 'authenticated'])

    def lazada_datamoat_toggle(self):
        icp_sudo = self.env['ir.config_parameter'].sudo()
        current_app_key = icp_sudo.get_param('lazop.app_key')

        if current_app_key:
            if self.lz_app_key != current_app_key:
                raise UserError(
                    "There are other Lazada accounts already enabling Datamoat, you can only enable datamoat "
                    "for a single account at a time!")
            else:
                icp_sudo.set_param('lazop.app_key', '')
        else:
            icp_sudo.set_param('lazop.app_key', self.lz_app_key)

        return {'type': 'ir.actions.client', 'tag': 'reload'}

