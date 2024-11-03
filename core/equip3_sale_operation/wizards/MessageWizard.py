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


class ChatMessageWizard(models.TransientModel):
    ''' Partner required '''
    _inherit = 'acrux.chat.message.wizard'

    attachment_ids = fields.Many2many(
        'ir.attachment', 'send_whatsapp_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    sale_id = fields.Many2one('sale.order', string='sale')
    mobile = fields.Char('Mobile')
    message_mass_id = fields.Many2one('send.message.mass', string='Message Mass')

    @api.model
    def default_get(self, default_fields):
        res = super(ChatMessageWizard, self).default_get(default_fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'sale.order' or context.get('custom_model') == 'sale.order':
            sale_order_id = self.env['sale.order'].browse(context.get('active_ids'))
            if not sale_order_id:
                sale_order_id = self.env['sale.order'].browse(context.get('sale_id'))
                res['mobile'] = sale_order_id.partner_id.mobile
            res['sale_id'] = sale_order_id.id
            template_id = sale_order_id._find_mail_template()
            template_values = self.env['mail.template'].browse(template_id).generate_email(sale_order_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[sale_order_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
            if sale_order_id.state in ['draft', 'quotation_approved']:
                # res['text'] = 'Hello,\n' + \
                #         'Your Order ' + sale_order_id.name +' amounting in '+ str(sale_order_id.amount_total) +' is Approved.\n' + \
                #         'Do not hestitate to contact us if you have any questions.'
                res['text'] = 'Hello, ' + \
                        'Your Order ' + sale_order_id.name +' amounting in '+ str(sale_order_id.amount_total) +' is Approved. ' + \
                        'Do not hestitate to contact us if you have any questions.'
            elif sale_order_id.state == 'sale':
                # res['text'] = 'Hello,\n' + \
                #         'Your Order ' + sale_order_id.name +' amounting in '+ str(sale_order_id.amount_total) +' is Confirmed.\n' + \
                #         'Do not hestitate to contact us if you have any questions.'
                res['text'] = 'Hello, ' + \
                        'Your Order ' + sale_order_id.name +' amounting in '+ str(sale_order_id.amount_total) +' is Confirmed. ' + \
                        'Do not hestitate to contact us if you have any questions.'
        elif context.get('active_model') == "account.move":
            move_id = self.env['account.move'].browse(context.get('active_ids'))
            template_id = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            template_values = self.env['mail.template'].browse(template_id.id).generate_email(move_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[move_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
            if move_id.state == 'posted':
                # res['text'] = 'Hello,\n' + \
                #               'Your Invoice ' + move_id.name +' amounting in '+ str(move_id.amount_total) +' is Posted.\n' + \
                #               'Do not hestitate to contact us if you have any questions.\n'
                res['text'] = 'Hello, ' + \
                              'Your Invoice ' + move_id.name +' amounting in '+ str(move_id.amount_total) +' is Posted. ' + \
                              'Do not hestitate to contact us if you have any questions. '
        if not res.get('text', False):
            res['text'] = 'text'
        return res

    def send_message_wizard(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = ''

        context = dict(self.env.context) or {}
        if context.get('active_model') == 'sale.order':
            sale_order_id = self.env['sale.order'].browse(context.get('active_ids'))
            template_id = sale_order_id._find_mail_template()
            lang = self.env.context.get('lang')
            template = self.env['mail.template'].browse(template_id)
            if template.lang:
                lang = template._render_lang(sale_order_id.ids)[sale_order_id.id]

            if sale_order_id.state != 'sale':
                subject = '%s Quotation (Ref %s)'%(sale_order_id.company_id.name, sale_order_id.name)
            else:
                subject = '%s Order (Ref %s)'%(sale_order_id.company_id.name, sale_order_id.name)

            body = plaintext2html(self.text)
            ctx = {
                'default_body': body,
                'default_subject': subject,
                'default_model': 'sale.order',
                'default_partner_ids': sale_order_id.partner_id.ids,
                'default_res_id': sale_order_id.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'custom_layout': "mail.mail_notification_paynow",
                'proforma': self.env.context.get('proforma', False),
                'force_email': False,
            }
            mail_compose_message_id = self.env['mail.compose.message'].with_context(ctx).create({})
            values = mail_compose_message_id.generate_email_for_composer(
                template.id, [sale_order_id.id],
                ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
            )[sale_order_id.id]
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'sale.order',
                    'res_id': sale_order_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            mail_compose_message_id.attachment_ids = [(6, 0, attachment_ids)]
            mail_compose_message_id.send_mail()
        if context.get('active_model') == 'account.move':
            move_id = self.env['account.move'].browse(context.get('active_ids'))
            template_id = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            lang = self.env.context.get('lang')
            template = self.env['mail.template'].browse(template_id.id)
            if template.lang:
                lang = template._render_lang(move_id.ids)[move_id.id]

            subject = '%s Invoice (Ref %s)'%(move_id.company_id.name, move_id.name)

            body = plaintext2html(self.text)
            ctx = {
                'default_body': body,
                'default_subject': subject,
                'default_model': 'account.move',
                'default_partner_ids': move_id.partner_id.ids,
                'default_res_id': move_id.ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id.id,
                'default_composition_mode': 'comment',
                'custom_layout': "mail.mail_notification_paynow",
                'force_email': False,
            }
            mail_compose_message_id = self.env['mail.compose.message'].with_context(ctx).create({})
            values = mail_compose_message_id.generate_email_for_composer(
                template.id, [move_id.id],
                ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id']
            )[move_id.id]
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'account.move',
                    'res_id': move_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            mail_compose_message_id.attachment_ids = [(6, 0, attachment_ids)]
            mail_compose_message_id.send_mail()
        if self.attachment_ids:
            self.text += ' Attachment: '
            random_num = random.randint(111111111, 999999999)
            for attachment in self.attachment_ids:
                password_attachment = self.generate_password_pdf(attachment, random_num)
                final_url = base_url + '/attachment/download/%d'%(password_attachment.id)
                url += final_url + '. '
            self.text += url
            self.text += 'password: %d' %(random_num)
        return super(ChatMessageWizard, self).send_message_wizard()

    def generate_password_pdf(self, attachment, password):
        output_pdf = PdfFileWriter()
        in_buff = io.BytesIO(base64.b64decode(attachment.datas))
        pdf = PdfFileReader(in_buff)
        output_pdf.appendPagesFromReader(pdf)
        output_pdf.encrypt(str(password), owner_pwd=None, use_128bit=True)
        buff = io.BytesIO()
        output_pdf.write(buff)
        value = buff.getvalue()
        attachment.write({
            'datas': base64.b64encode(value),
        })
        return attachment


    def send_message_wizard_mass(self):
        self.ensure_one()
        conv_id = self.conversation_id
        if not conv_id:
            Conv = self.env['acrux.chat.conversation']
            conv_id = Conv.conversation_create(self.partner_id, self.connector_id.id, self.mobile)
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

    @api.onchange('sale_id', 'partner_id')
    def _onchange_sale_id_partner_id(self):
        for rec in self:
            if rec.sale_id:
                rec.partner_id = rec.sale_id.partner_id

            if rec.partner_id:
                rec.mobile = rec.partner_id.mobile


class WhatsappSendMessage(models.TransientModel):
    _inherit = 'whatsapp.message.wizard'

    attachment_ids = fields.Many2many(
        'ir.attachment', 'whatsapp_message_compose_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    message_send = fields.Boolean(string='Message Send')

    @api.model
    def default_get(self, default_fields):
        res = super(WhatsappSendMessage, self).default_get(default_fields)
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
                    'expiry_date': datetime.now(),
                    'res_model': 'sale.order',
                    'res_id': sale_order_id.id,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
            if sale_order_id.state in ['draft', 'quotation_approved']:
                res['message'] = 'Hello,\n' + \
                              'Your Order Number ' + sale_order_id.name +' with amount '+ str(sale_order_id.amount_total) +' is Approved.\n' + \
                              'Your order date and time is ' + str(sale_order_id.date_order) + \
                              '\nIf you have any questions, please do not hesitate to contact us.\n'
            elif sale_order_id.state == 'sale':
                res['message'] = 'Hello,\n' + \
                              'Your Order Number ' + sale_order_id.name +' with amount '+ str(sale_order_id.amount_total) +' is Confirmed.\n' + \
                              'Your order date and time is ' + str(sale_order_id.date_order) + \
                              '\nIf you have any questions, please do not hesitate to contact us.\n'
        elif context.get('active_model') == "account.move":
            move_id = self.env['account.move'].browse(context.get('active_ids'))
            template_id = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            template_values = self.env['mail.template'].browse(template_id.id).generate_email(move_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in template_values[move_id.id].pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'expiry_date': datetime.now(),
                    'res_model': 'account.move',
                    'res_id': move_id.id,
                    'type': 'binary',
                }
                attachment_id = Attachment.create(data_attach)
                attachment_id.generate_access_token()
                attachment_ids.append(attachment_id.id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
            if move_id.state == 'posted':
                res['message'] = 'Hello,\n' + \
                              'Your Invoice number ' + move_id.name +' with amount '+ str(move_id.amount_total) +' is Posted.\n' + \
                              'Your invoice date and time is ' + str(move_id.invoice_date) + \
                              '\nIf you have any questions, please do not hesitate to contact us.\n'
        return res

    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        context = dict(self.env.context) or {}
        if context.get('active_model') != "sale.order" and context.get('active_model') != "account.move":
            return super(WhatsappSendMessage, self).onchange_template_id_wrapper()

    def generate_email_for_composer(self, template_id, res_ids, fields=None):
        context = dict(self.env.context) or {}
        if context.get('active_model') != "sale.order" and context.get('active_model') != "account.move":
            return super(WhatsappSendMessage, self).generate_email_for_composer(template_id, res_ids, fields=fields)

    def send_message(self):
        context = dict(self.env.context) or {}
        sale_order_model = context.get('active_model') == 'sale.order'
        account_move_model = context.get('active_model') == 'account.move'
        if self.message_send:
            raise ValidationError(_("Can't send attachment twice, please close the wizard first"))
        if self.message and self.mobile_number:
            if self.attachment_ids:
                if (sale_order_model or account_move_model):
                    self.message += '\nAttachment:\n'
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                url = '\n'
                random_num = random.randint(111111111, 999999999)
                if (sale_order_model or account_move_model):
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

    def generate_password_pdf(self, attachment, password):
        output_pdf = PdfFileWriter()
        in_buff = io.BytesIO(base64.b64decode(attachment.datas))
        pdf = PdfFileReader(in_buff)
        output_pdf.appendPagesFromReader(pdf)
        output_pdf.encrypt(str(password), owner_pwd=None, use_128bit=True)
        buff = io.BytesIO()
        output_pdf.write(buff)
        value = buff.getvalue()
        attachment.write({
            'datas': base64.b64encode(value),
        })
        return attachment

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    expiry_date = fields.Datetime(string="Expiry Date")
