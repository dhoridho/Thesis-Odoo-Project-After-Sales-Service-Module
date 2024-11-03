# -*- coding: utf-8 -*-
import json
import requests
from odoo import models, api
from odoo.addons.acrux_chat.tools import get_image_from_url


class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    @api.model
    def create(self, vals):
        if vals.get('connector_id') and vals.get('number'):
            conn_id = self.env['acrux.chat.connector'].browse([vals.get('connector_id')])
            if conn_id.connector_type == 'chatapi':
                param = {'chatId': '%s@c.us' % vals.get('number').strip('+')}
                try:
                    data = conn_id.ca_request('get', 'dialog', param, timeout=10)
                    image_url = data.get('image')
                    if image_url and image_url.startswith('http'):
                        raw = get_image_from_url(image_url)
                        if raw:
                            vals.update({'image_128': raw})
                except Exception as e:
                    pass
        return super(AcruxChatConversation, self).create(vals)

    def conversation_send_read(self):
        super(AcruxChatConversation, self).conversation_send_read()
        for conv_id in self:
            conn_id = conv_id.connector_id
            if conn_id.connector_type == 'chatapi':
                try:
                    url = conn_id.ca_get_endpoint('readChat')
                    header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
                    data = json.dumps({'phone': conv_id.number.lstrip('+')})
                    requests.post(url, data=data, headers=header, timeout=1, verify=conn_id.verify)
                except Exception as _e:
                    pass
