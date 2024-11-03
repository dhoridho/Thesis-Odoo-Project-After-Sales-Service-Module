# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    conversation_id = fields.Many2one('acrux.chat.conversation', 'ChatRoom', ondelete='set null')

    def send_invoice_by_chat(self):
        self.ensure_one()
        inv_id = self.invoice_ids[0].with_context(conversation_id=self.conversation_id.id)
        if inv_id:
            conversation_not_exist = inv_id.send_by_chatroom()
            return conversation_not_exist or True
        else:
            raise ValidationError(_('Invoice does not exist.'))

    def send_by_chatroom(self):
        self.ensure_one()
        if not self.conversation_id:
            conv_ids = self.partner_id.contact_ids
            if len(conv_ids) == 1:
                self.conversation_id = conv_ids[0].id
            elif len(conv_ids) > 1:
                return {'name': _('Conversation'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'acrux.chat.select.conversation.wizard',
                        'target': 'new',
                        'context': dict(conversation_ids=conv_ids.ids, sale_order_id=self.id)}

        if self.conversation_id:
            Attachment = self.env['ir.attachment']
            conv_id = self.conversation_id
            conv_id.with_context(no_send_read=True).block_conversation()
            report_id = conv_id.connector_id.sale_report_id or self.env.ref('sale.action_report_saleorder')
            pdf = report_id._render_qweb_pdf(self.id)
            attac_id = name = False
            if report_id.attachment:
                attac_id = report_id.retrieve_attachment(self)
                attac_id.write({'delete_old': True})
                name = attac_id.name
            if not attac_id:
                b64_pdf = base64.b64encode(pdf[0])
                name = ((self.state in ('draft', 'sent') and _('Quotation - %s') % self.name) or
                        _('Order - %s') % self.name)
                name = '%s.pdf' % name
                attac_id = Attachment.create({'name': name,
                                              'type': 'binary',
                                              'datas': b64_pdf,
                                              'store_fname': name,
                                              'res_model': 'acrux.chat.message',
                                              'res_id': 0,
                                              'delete_old': True, })
            body = _('Sent to ChatRoom: %s (%s).') % (conv_id.name, conv_id.number_format)
            self.message_post(body=body, subject=name, attachment_ids=[attac_id.id])
            msg_data = {
                'ttype': 'file',
                'from_me': True,
                'contact_id': conv_id.id,
                'res_model': 'ir.attachment',
                'res_id': attac_id.id,
                'text': name,
                'event': 'order_sent',
            }
            conv_id.send_message_and_bus(msg_data)
