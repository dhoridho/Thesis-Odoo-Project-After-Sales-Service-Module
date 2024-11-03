# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class SelectConversationWizard(models.TransientModel):
    _name = 'acrux.chat.select.conversation.wizard'
    _description = 'Select Conversation and Send'

    conversation_id = fields.Many2one('acrux.chat.conversation', string='Select Conversation',
                                      required=True, ondelete='cascade',
                                      domain=lambda self: [('id', 'in', self._context.get('conversation_ids'))])

    def save_and_send(self):
        sale_order_id = self._context.get('sale_order_id')
        invoice_id = self._context.get('invoice_id')
        if sale_order_id:
            order_id = self.env['sale.order'].browse([sale_order_id])
            order_id.conversation_id = self.conversation_id.id
            order_id.send_by_chatroom()
        elif invoice_id:
            conv_id = self.env['account.move'].with_context(conversation_id=self.conversation_id.id)
            conv_id.browse([invoice_id]).send_by_chatroom()
        else:
            raise ValidationError(_('Missing parameters'))
