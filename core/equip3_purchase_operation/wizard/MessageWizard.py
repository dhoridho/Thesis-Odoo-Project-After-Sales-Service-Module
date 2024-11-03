# -*- coding: utf-8 -*-
import random
import pytz
import base64
import io
from datetime import datetime, time, timedelta
from pytz import timezone, UTC
from odoo.exceptions import ValidationError
from odoo.tools import plaintext2html
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from PyPDF2 import  PdfFileReader, PdfFileWriter


class WhatsappSendMessage(models.TransientModel):
    _inherit = 'whatsapp.message.wizard'

    attachment_ids = fields.Many2many(
        'ir.attachment', 'whatsapp_message_compose_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')

    @api.model
    def default_get(self, default_fields):
        res = super(WhatsappSendMessage, self).default_get(default_fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == "purchase.order":
            order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            ir_model_data = self.env['ir.model.data']
            if order_id.state != 'purchase':
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
            template_values = self.env['mail.template'].browse(template_id).generate_email(order_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[order_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'purchase.order',
                    'res_id': order_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
        return res

    def send_message(self):
        context = dict(self.env.context) or {}
        purchase_order_model = context.get('active_model') == "purchase.order"
        if purchase_order_model:
            order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            if order_id.state != 'purchase':
                order_id.write({'state': 'sent'})
            if self.message_send:
                raise ValidationError(_("Can't send attachment twice, please close the wizard first"))
            if self.message and self.mobile_number:
                if self.attachment_ids:
                    if purchase_order_model:
                        self.message += '\nAttachment:\n'
                    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    url = '\n'
                    random_num = random.randint(111111111, 999999999)
                    if purchase_order_model:
                        for attachment in self.attachment_ids:
                            password_attachment = self.generate_password_pdf(attachment, random_num)
                            final_url = base_url + '/attachment/download/%d'%(password_attachment.id)
                            url += final_url + '\n'
                        self.message += url
                        self.message += '\npassword: %d' %(random_num)
                message_string = ''
                message = self.message.split('\n')
                for msg in message:
                    message_string = message_string + msg + '%0a'
                message_string = message_string[:(len(message_string) - 3)]
                number = self.user_id.mobile
                link = "https://web.whatsapp.com/send?phone=" + number
                self.message_send = True
                send_msg = {
                    'type': 'ir.actions.act_url',
                    'url': link + "&text=" + message_string,
                    'target': 'new',
                    'res_id': self.id,
                }

                return send_msg
        else:
            return super(WhatsappSendMessage, self).send_message()


class ChatMessageWizard(models.TransientModel):
    _inherit = 'acrux.chat.message.wizard'
    
    attachment_ids = fields.Many2many(
        'ir.attachment', 'send_whatsapp_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')

    @api.model
    def default_get(self, default_fields):
        res = super(ChatMessageWizard, self).default_get(default_fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == "purchase.order":
            order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            ir_model_data = self.env['ir.model.data']
            if order_id.state != 'purchase':
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference('purchase', 'email_template_edi_purchase_done')[1]
            template_values = self.env['mail.template'].browse(template_id).generate_email(order_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[order_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'purchase.order',
                    'res_id': order_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
            if order_id.state != 'purchase':
                res['text'] = 'Hello,\n' + \
                            'This is about the Request for Quotation ' + order_id.name +' amounting in '+ str(order_id.amount_total) +' from ' + order_id.company_id.name + '.\n' \
                            'The order date and time is ' + str(order_id.date_order) + '\n' + 'If you have any questions, please do not hesitate to contact us \n' + 'Best Regards,\n'
            else:
                res['text'] = 'Hello,\n' + \
                            'This is about the Purchase Order ' + order_id.name +' amounting in '+ str(order_id.amount_total) +' from ' + order_id.company_id.name + '.\n' \
                            'The order date and time is ' + str(order_id.date_order) + '\n' + 'If you have any questions, please do not hesitate to contact us \n' + 'Best Regards,\n'
        return res

    def send_message_wizard(self):
        context = dict(self.env.context) or {}
        res = super(ChatMessageWizard, self).send_message_wizard()
        if context.get('active_model') == 'purchase.order':
            purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            if purchase_order_id.state != 'purchase':
                purchase_order_id.write({'state' : 'sent'})
        return res
