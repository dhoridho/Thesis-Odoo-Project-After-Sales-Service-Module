# -*- coding: utf-8 -*-
from odoo import models
from odoo import fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    acrux_chat_active = fields.Boolean('Active in Chat', default=True)

    def toggle_acrux_chat_active(self):
        for r in self:
            r.acrux_chat_active = not r.acrux_chat_active
        self.notify_status_changed()

    def set_chat_active(self, value):
        value = value.get('acrux_chat_active')
        self.sudo().acrux_chat_active = value
        self.notify_status_changed()

    def notify_status_changed(self):
        status_data = list(map(lambda r: {'sellman_id': [r.id, r.name],
                                          'status': r.acrux_chat_active}, self))
        if status_data:
            data_to_send = {'change_status': status_data}
            channel = (self._cr.dbname, 'acrux.chat.conversation', self.id)
            self.env['bus.bus'].sendone(channel, data_to_send)
