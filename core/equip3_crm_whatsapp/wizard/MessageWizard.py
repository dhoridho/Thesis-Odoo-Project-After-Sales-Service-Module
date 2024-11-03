# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ChatMessageWizard(models.TransientModel):
    ''' Partner required '''
    _inherit = 'acrux.chat.message.wizard'
    
    attachment_ids = fields.Many2many(
        'ir.attachment', 'send_whatsapp_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')


    @api.model
    def default_get(self, default_fields):
        res = super(ChatMessageWizard, self).default_get(default_fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'sale.order':
            sale_order_id = self.env['sale.order'].browse(context.get('active_ids'))
            template_id = sale_order_id._find_mail_template()
            template_values = self.env['mail.template'].browse(template_id).generate_email(sale_order_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[sale_order_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
        return res

    def send_message_wizard(self):
        self.ensure_one()
        conv_id = self.conversation_id
        if not conv_id:
            if not self.connector_id:
                raise ValidationError(_('Please select Channel to send message.'))
            Conv = self.env['acrux.chat.conversation']
            conv_id = Conv.conversation_create(self.partner_id, self.connector_id.id)
        conv_id.with_context(no_send_read=True).block_conversation()
        template_obj = self.env['qiscus.template'].search([('name', '=', 'hm_notification_template')],
                                                          limit=1)
        msg_data = {
            'ttype': 'text',
            'from_me': True,
            'contact_id': conv_id.id,
            'text': self.text,
            'template_id': template_obj.id,
        }
        conv_id.send_message(msg_data)

