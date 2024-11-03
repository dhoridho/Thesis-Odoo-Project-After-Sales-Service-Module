# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockScrapRequest(models.Model):
    _inherit = 'stock.scrap.request'

    auto_scrap_notification = fields.Many2many(
        'res.users', related='warehouse_id.responsible_users', string="Auto-Scrap Notification Send to")

    def _delete_scrap_confirmed(self):
        scrap = self.env['stock.scrap.request'].search(
            [('state', '=', 'confirmed'), ('create_uid', '=', 1)])
        if scrap:
            scrap.unlink()
