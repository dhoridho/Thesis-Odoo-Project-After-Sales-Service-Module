# -*- coding: utf-8 -*-
import base64
from odoo import models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def send_by_chatroom(self):
        self.ensure_one()
        conv_id = self._context.get('conversation_id')
        if conv_id:
            conv_id = self.env['acrux.chat.conversation'].browse([conv_id])
        if not conv_id:
            conv_ids = self.partner_id.contact_ids
            if len(conv_ids) == 1:
                conv_id = conv_ids[0]
            elif len(conv_ids) > 1:
                return {'name': _('Conversation'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'acrux.chat.select.conversation.wizard',
                        'target': 'new',
                        'context': dict(conversation_ids=conv_ids.ids, invoice_id=self.id)}
        if conv_id:
            Attachment = self.env['ir.attachment']
            conv_id.with_context(no_send_read=True).block_conversation()
            invoice_print = self.action_invoice_print()
            report_name = (invoice_print or {}).get('report_name')
            if not report_name:
                raise ValidationError(_('Configure Reports.'))
            report_id = self.env['ir.actions.report']._get_report_from_name(report_name)
            pdf = report_id._render_qweb_pdf(self.id)
            attac_id = name = False
            if report_id.attachment:
                attac_id = report_id.retrieve_attachment(self)
                if attac_id:
                    attac_id.write({'delete_old': True})
                    name = attac_id.name
            if not attac_id:
                b64_pdf = base64.b64encode(pdf[0])
                name = (self._get_report_base_filename() or self.name or 'INV').replace('/', '_') + '.pdf'
                attac_id = Attachment.create({'name': name,
                                              'type': 'binary',
                                              'datas': b64_pdf,
                                              'store_fname': name,
                                              'res_model': 'acrux.chat.message',
                                              'res_id': 0,
                                              'delete_old': True})
            body = _('Sent to ChatRoom: %s (%s).') % (conv_id.name, conv_id.number_format)
            self.message_post(body=body, subject=name, attachment_ids=[attac_id.id])
            msg_data = {
                'ttype': 'file',
                'from_me': True,
                'contact_id': conv_id.id,
                'res_model': 'ir.attachment',
                'res_id': attac_id.id,
                'text': name,
                'event': 'inv_sent',
            }
            conv_id.send_message_and_bus(msg_data)
