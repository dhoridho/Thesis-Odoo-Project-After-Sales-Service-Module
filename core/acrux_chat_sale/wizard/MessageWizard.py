# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ChatMessageWizard(models.TransientModel):
    ''' Partner required '''
    _name = 'acrux.chat.message.wizard'
    _description = 'ChatRoom Message'

    text = fields.Text('Message', required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    conversation_id = fields.Many2one('acrux.chat.conversation', string='ChatRoom', ondelete='set null')
    connector_id = fields.Many2one('acrux.chat.connector', string='Channel', ondelete='set null')

    @api.model
    def default_get(self, default_fields):
        vals = super(ChatMessageWizard, self).default_get(default_fields)
        partner_id = self._context.get('default_partner_id')
        if not partner_id:
            raise ValidationError(_('Partner is required.'))
        partner_id = self.env['res.partner'].browse([partner_id])
        if partner_id.contact_ids:
            vals['conversation_id'] = partner_id.contact_ids[0].id
        return vals

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        return {
            'domain': {'conversation_id': [('res_partner_id', '=', self.partner_id.id)]},
        }

    @api.onchange('connector_id')
    def onchange_connector_id(self):
        data = [('res_partner_id', '=', self.partner_id.id)]
        if self.connector_id:
            data.append(('connector_id', '=', self.connector_id.id))
            self.conversation_id = False
        return {
            'domain': {'conversation_id': data},
        }

    def send_message_wizard(self):
        self.ensure_one()
        conv_id = self.conversation_id
        if not conv_id:
            if not self.connector_id:
                raise ValidationError(_('Please select Channel to send message.'))
            Conv = self.env['acrux.chat.conversation']
            conv_id = Conv.conversation_create(self.partner_id, self.connector_id.id)
        conv_id.with_context(no_send_read=True).block_conversation()
        msg_data = {
            'ttype': 'text',
            'from_me': True,
            'contact_id': conv_id.id,
            'text': self.text,
        }
        conv_id.send_message(msg_data)
