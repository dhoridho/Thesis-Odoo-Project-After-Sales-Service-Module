# -*- coding: utf-8 -*-
import base64
import re
import os
import shutil
import requests
import json
import time
from werkzeug.utils import secure_filename
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from odoo.tools import formatLang
from odoo.addons.acrux_chat.tools import get_binary_attach
from requests_toolbelt import MultipartEncoder

API3_ENDPOINT = "https://api3.qiscus.com/api/v2/sdk"


class QiscussMessage(models.Model):
    _inherit = 'acrux.chat.message'

    # ttype = fields.Selection(selection_add=[('template', 'Template')],
    #                          ondelete={'template': 'cascade'})
    template_id = fields.Many2one('qiscus.template', string='Template ID')
    is_direct = fields.Boolean('is Direct', default=False)
    comment_id = fields.Char('Comment ID')

    # @api.model
    # def default_get(self, fields):
    #     res = super(QiscussMessage, self).default_get(fields)
    #     template_obj = self.env['qiscus.template'].search([('name', '=', 'hm_notification_template')], limit=1)
    #     res.update({
    #         'template_id': template_obj.id
    #     })
    #     return res

    @api.model
    def clean_number(self, number):
        return number.replace('+', '').replace(' ', '').replace('-', '')

    # @api.model
    def qc_ttype_text_custom(self):
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        header = {'Content-Type': 'application/json'}
        ret = {
            'to': int(self.clean_number(self.contact_id.number)),
            'recipient_type': 'individual',
            'type': 'text',
            'text': {
                'body': self.text
            }
            # 'phone': self.clean_number(self.contact_id.number),
            # 'body': self.text,
        }
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_text(self):
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        if not self.template_id:
            raise ValidationError('Template record does not exist or has been deleted')
        content_obj = self.env['qiscus.template.content'].search([('template_id', '=', self.template_id.id)], limit=1)
        template_content = content_obj.content
        count_var = len(re.findall(r'.[{{]\d[}}]+', template_content))
        if 'chatroom_default_answer_text' in self.template_id.name:
            self.text = '%s\n%s' % (self.contact_id.name, self.text)
        messages = self.text.split('\n')
        count_message = 0
        message_obj = []
        for pesan in messages:
            message_obj.append({
                'type': 'text',
                'text': pesan
            })
            count_message += 1
        if count_message != count_var:
            raise ValidationError('Record does not match the specified template variable.')
        header = {'Content-Type': 'application/json'}
        ret = {
            'to': int(self.clean_number(self.contact_id.number)),
            'recipient_type': 'individual',
            'type': 'template',
            'template': {
                'namespace': self.template_id.namespace,
                'name': self.template_id.name,
                'language': {
                    'policy': "deterministic",
                    'code': 'en'
                },
                'components': [{
                    'type': 'body',
                    'parameters': message_obj
                    # 'parameters': [{
                    #     'type': 'text',
                    #     'text': self.text
                    # }]
                }]
            }
        }
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_audio(self):
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        # Only suport 'audio/ogg; codecs=opusg'
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        sdk_token = connector_id.qc_sdk_token
        ret = {
            'recipient_type': 'individual',
            'to': int(self.clean_number(self.contact_id.number)),
            'type': 'audio',
        }
        if attach_id.mimetype and attach_id.mimetype in ['audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg']:
            # data:image/jpeg;base64,/9j/4AAQ...
            store_file = attach_id.store_fname
            file_fullpath = attach_id._full_path(store_file)
            filetype = attach_id.mimetype.split('/')
            apptype = filetype[0].strip()
            contenttype = filetype[1].strip()
            file_fullpath_ext = '%s.%s' % (file_fullpath, contenttype)
            strtype = filetype[0].strip()
            body_upload = {
                'data-binary': 'data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii')),
            }
            header_upfile = {
                'Content-Type': attach_id.mimetype,
                'Qiscus-App-Id': connector_id.qc_app_name,
                'Qiscus-Secret-Key': connector_id.apikey
            }
            result = connector_id.qc_request('post', f'whatsapp/v1/{app_id}/{channel_id}/media', body_upload, header_upfile)
            if 'media' in result:
                media_ids = result.get('media')
                for media_id in media_ids:
                    ret.update({
                        'audio': {
                            'id': media_id.get('id'),
                        }
                    })
            else:
                raise ValidationError('The video can not send to media server.')
            #
            # shutil.copy(file_fullpath, file_fullpath_ext)
            # name_img = os.path.basename(file_fullpath_ext)
            # mp_encoder = MultipartEncoder(
            #     fields={
            #         'file': (name_img, open(file_fullpath_ext, 'rb'), 'multipart/form-data')
            #     }
            # )
            # header_upfile = {
            #     'Qiscus-Sdk-App-Id': app_id,
            #     'Qiscus-Sdk-Token': sdk_token,
            #     'Content-Type': mp_encoder.content_type,
            #     'sec-fetch-mode': 'cors'
            # }
            # with requests.Session() as s:
            #     result = s.post(API3_ENDPOINT + '/upload', data=mp_encoder, headers=header_upfile)
            # res_img = json.loads(result.text)
            # link_url = False
            # if res_img:
            #     if res_img['status'] != 200:
            #         raise ValidationError(res_img['message'])
            #     link_url = res_img['results']['file']['url']
            header = {
                'Content-Type': 'application/json'
            }
            # ret.update({
            #     'audio': {
            #         'link': link_url,
            #         'caption': self.text or '',
            #     }
            # })

            return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]
        else:
            raise ValidationError("MIME type not supported message.")

        # if attach_id.mimetype == 'audio/ogg':
        #     # data:audio/ogg;base64,/9j/4AAQ...
        #     ret['audio'] = 'data:audio/ogg;base64,%s' % attach_id.datas.decode('ascii')
        # else:
        #     # raise error ?
        #     ret['audio'] = url
        # return [ret, 'sendPTT', False]

    @api.model
    def qc_ttype_image(self, mimetype=False, content=False):
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        ret = {
            'recipient_type': 'individual',
            'to': int(self.clean_number(self.contact_id.number)),
            'type': 'image',
        }
        if mimetype == 'url':
            header = {
                'Content-Type': 'application/json'
            }
            ret.update({
                'image': {
                    'link': content,
                    'caption': self.text or '',
                }
            })
        else:
            filetype = mimetype.split('/')
            strtype = filetype[0].strip()
            body_upload = {
                'data-binary': content
            }
            header_img = {
                'Content-Type': mimetype,
                'Qiscus-App-Id': connector_id.qc_app_name,
                'Qiscus-Secret-Key': connector_id.apikey
            }
            result = connector_id.qc_request('post', f'whatsapp/v1/{app_id}/{channel_id}/media', body_upload, header_img)
            if 'media' in result:
                media_ids = result.get('media')
                header = {
                    'Content-Type': 'application/json',
                }
                for media_id in media_ids:
                    ret.update({
                        'image': {
                            'id': media_id.get('id'),
                            'caption': self.text or '',
                        }
                    })
            else:
                raise ValidationError('The image can not send to media server.')
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_video(self, mimetype=False, content=False):
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ret = {
            'recipient_type': 'individual',
            'to': int(self.clean_number(self.contact_id.number)),
            'type': 'video',
        }
        if mimetype == 'url':
            header = {
                'Content-Type': 'application/json'
            }
            ret.update({
                'video': {
                    'link': content,
                    'caption': self.text or '',
                }
            })
        else:
            filetype = mimetype.split('/')
            strtype = filetype[0].strip()
            body_upload = {
                'data-binary': content,
            }
            header_img = {
                'Content-Type': mimetype,
                'Qiscus-App-Id': connector_id.qc_app_name,
                'Qiscus-Secret-Key': connector_id.apikey
            }
            result = connector_id.qc_request('post', f'whatsapp/v1/{app_id}/{channel_id}/media', body_upload, header_img)
            if 'media' in result:
                media_ids = result.get('media')
                header = {
                    'Content-Type': 'application/json'
                }
                for media_id in media_ids:
                    ret.update({
                        'video': {
                            'id': media_id.get('id'),
                            'caption': self.text or '',
                        }
                    })
            else:
                raise ValidationError('The video can not send to media server.')
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_document(self, mimetype=False, content=False):
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ret = {
            'recipient_type': 'individual',
            'to': int(self.clean_number(self.contact_id.number)),
            'type': 'document',
        }
        if mimetype == 'url':
            header = {
                'Content-Type': 'application/json'
            }
            ret.update({
                'document': {
                    'link': content,
                    'caption': self.text or '',
                }
            })
        else:
            filetype = mimetype.split('/')
            strtype = filetype[0].strip()
            header_image = {
                'Content-Type': mimetype,
                'Qiscus-App-Id': connector_id.qc_app_name,
                'Qiscus-Secret-Key': connector_id.apikey
            }
            body_upload = {
                'data-binary': content
            }
            result = connector_id.qc_request('post', f'whatsapp/v1/{app_id}/{channel_id}/media', body_upload, header_image)
            if 'media' in result:
                media_ids = result.get('media')
                header = {
                    'Content-Type': 'application/json'
                }
                for media_id in media_ids:
                    ret.update({
                        'document': {
                            'id': media_id.get('id'),
                            'caption': self.text or '',
                        }
                    })
            else:
                raise ValidationError('The document can not send to media server.')
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_file(self):
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        sdk_token = connector_id.qc_sdk_token
        if attach_id.mimetype:
            # data:image/jpeg;base64,/9j/4AAQ...
            store_file = attach_id.store_fname
            file_fullpath = attach_id._full_path(store_file)
            filetype = attach_id.mimetype.split('/')
            apptype = filetype[0].strip()
            contenttype = filetype[1].strip()
            file_fullpath_ext = '%s.%s' % (file_fullpath, contenttype)
            shutil.copy(file_fullpath, file_fullpath_ext)
            name_img = os.path.basename(file_fullpath_ext)
            mp_encoder = MultipartEncoder(
                fields={
                    'file': (name_img, open(file_fullpath_ext, 'rb'), 'multipart/form-data')
                }
            )
            header_upfile = {
                'Qiscus-Sdk-App-Id': app_id,
                'Qiscus-Sdk-Token': sdk_token,
                'Content-Type': mp_encoder.content_type,
                'sec-fetch-mode': 'cors'
            }
            with requests.Session() as s:
                result = s.post(API3_ENDPOINT + '/upload', data=mp_encoder, headers=header_upfile)
            res_img = json.loads(result.text)
            link_url = False
            if res_img:
                if res_img['status'] != 200:
                    raise ValidationError(res_img['message'])
                link_url = res_img['results']['file']['url']

            if apptype == 'image' and attach_id.mimetype in ['image/jpeg', 'image/png']:
                # return self.qc_ttype_image(mimetype=attach_id.mimetype, content='data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii')))
                return self.qc_ttype_image(mimetype='url', content=link_url)
            elif apptype == 'video' and attach_id.mimetype in ['video/mp4', 'video/3gp']:
                # return self.qc_ttype_video(mimetype=attach_id.mimetype, content='data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii')))
                return self.qc_ttype_video(mimetype='url', content=link_url)
            elif apptype == 'application' and attach_id.mimetype in ['text/plain', 'application/pdf', 'application/vnd.ms-powerpoint',
                                                                     'application/msword', 'application/vnd.ms-excel',
                                                                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                                                     'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                                                                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
                # return self.qc_ttype_document(mimetype=attach_id.mimetype, content='data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii')))
                return self.qc_ttype_document(mimetype='url', content=link_url)
            else:
                # ret['body'] = 'data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii'))
                raise ValidationError("MIME type not supported message.")
        # else:
        #     ret['body'] = url
        # return [ret, 'sendFile', False]

    @api.model
    def qc_ttype_product(self):
        url = content_str = False
        mimetype = filename = ''
        image_field = 'image_chat'  # to set dynamic: self.res_filed
        if not self.res_id or self.res_model != 'product.product':
            raise ValidationError('Product type is required.')
        prod_id = self.env[self.res_model].browse(self.res_id)
        if not prod_id:
            raise ValidationError('Product is required.')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        # caption ----------
        # or prod_id.name_get()[0][1]
        list_price = formatLang(self.env, prod_id.list_price,
                                currency_obj=self.env.user.company_id.currency_id)
        caption = '%s\n%s / %s' % (self.text or prod_id.name.strip(),
                                   list_price, prod_id.uom_id.name)

        # image ----------
        field_image = getattr(prod_id, image_field)
        if field_image:
            content_str = field_image.decode('ascii')
            filename = secure_filename(prod_id.name)
            attach = get_binary_attach(self.env, self.res_model, self.res_id, image_field,
                                       fields_ret=['mimetype', 'file_size', 'store_fname'])
            attach_id, url = self.get_url_attach(attach['id'])
            size = attach_id and attach_id['file_size'] or len(base64.b64decode(content_str))
            mimetype = attach_id and attach_id['mimetype']
            if size:
                # self.message_check_weight(value=size, raise_on=True)
                limit, msg = 5000000, '5 Mb'
                if (size or 0) >= limit:
                    raise ValidationError(_('Attachment exceeds the maximum size allowed (%s).') % msg)
            if mimetype:
                ext = mimetype.split('/')
                if len(ext) == 2:
                    filename = secure_filename('%s.%s' % (prod_id.name, ext[1]))
            else:
                prod_id, url = self.get_url_image(res_model=self.res_model, res_id=self.res_id,
                                                  field=image_field, prod_id=prod_id)

        if not field_image or (not mimetype and not url):
            header = {
                'Content-Type': 'image/png'
            }
            ret = {
                'recipient_type': 'individual',
                'to': int(self.clean_number(self.contact_id.number)),
                'type': 'image',
                'image': {
                    'link': base_url + 'web/static/src/img/placeholder.png',
                    'caption': caption,
                }
            }
        else:
            store_file = attach_id and attach_id['store_fname']
            file_fullpath = attach_id._full_path(store_file)
            file_fullpath_ext = '%s.%s' % (file_fullpath, ext[1])
            shutil.copy(file_fullpath, file_fullpath_ext)
            name_img = os.path.basename(file_fullpath_ext)
            mp_encoder = MultipartEncoder(
                fields={
                    'file': (name_img, open(file_fullpath_ext, 'rb'), 'multipart/form-data')
                }
            )
            sdk_token = connector_id.qc_sdk_token
            header_img = {
                'Qiscus-Sdk-App-Id': app_id,
                'Qiscus-Sdk-Token': sdk_token,
                'Content-Type': mp_encoder.content_type,
                'sec-fetch-mode': 'cors'
            }
            with requests.Session() as s:
                result = s.post(API3_ENDPOINT + '/upload', data=mp_encoder, headers=header_img)
            res_img = json.loads(result.text)
            link_url = False
            if res_img:
                if res_img['status'] != 200:
                    raise ValidationError(res_img['message'])
                link_url = res_img['results']['file']['url']

            header = {
                'Content-Type': 'application/json'
            }
            ret = {
                'recipient_type': 'individual',
                'to': int(self.clean_number(self.contact_id.number)),
                'type': 'image',
                'image': {
                    'link': link_url,
                    'caption': caption,
                    # 'url': link_url,
                    # 'file_name': name_img,
                }
            }
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def qc_ttype_sale(self):
        if self.res_model != 'sale.order':
            raise ValidationError('Order type is required.')
        return self.qc_ttype_file()

    @api.model
    def qc_ttype_location(self):
        ''' Text format:
                name
                address
                latitude, longitude
        '''
        connector_id = self.contact_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        header= {
            'Content-Type': 'application/json'
        }
        parse = self.text.split('\n')
        if len(parse) != 3:
            return self.qc_ttype_text()
        cords = parse[2].split(',')
        ret = {
            'recipient_type': 'individual',
            'to': int(self.clean_number(self.contact_id.number)),
            'type': 'location',
            'location': {
                'name': parse[0].strip(),
                'address': parse[1].strip(),
                'latitude': cords[0].strip('( '),
                'longitude': cords[1].strip(') '),
            }
        }
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    def message_parse(self):
        message = super(QiscussMessage, self).message_parse()
        connector_id = self.contact_id.connector_id
        if connector_id.connector_type == 'qiscuss':
            if self.ttype == 'text':
                # if self.template_id:
                #     message = self.qc_ttype_text()
                # else:
                #     message = self.qc_ttype_text_custom()
                if self.is_direct:
                    message = self.qc_ttype_text_custom()
                else:
                    message = self.qc_ttype_text()
            elif self.ttype in ['image', 'video', 'file']:
                message = self.qc_ttype_file()
            elif self.ttype == 'audio':
                message = self.qc_ttype_audio()
            elif self.ttype == 'product':
                message = self.qc_ttype_product()
            elif self.ttype == 'sale_order':
                message = self.qc_ttype_sale()
            elif self.ttype == 'location':
                message = self.qc_ttype_location()
            elif self.ttype == 'contact':
                raise ValidationError('Not implemented')
        return message

    def qc_message_send(self, msgdata=None):
        ''' Call super at the beginning. '''
        # ret = super(QiscussMessage, self).message_send()
        self.ensure_one()
        if msgdata is not None:
            if not self.ttype.startswith('info'):
                self.qc_message_check_allow_send(msgdata)
            conversation_id = self.env['acrux.chat.conversation'].browse(msgdata.get('contact_id'))
            # connector_id = self.contact_id.connector_id
            connector_id = conversation_id.connector_id
            headers = {}
            [message, path, header] = self.message_parse()
            headers['Qiscus-App-Id'] = connector_id.qc_app_name
            headers['Qiscus-Secret-Key'] = connector_id.apikey
            if header:
                headers.update(header)
            result = connector_id.qc_request('post', path, message, headers)

            whatsappID = result.get('contacts')
            for wa in whatsappID:
                wa_id = wa.get('wa_id', False)

            messageId = result.get('messages')
            for msg in messageId:
                msg_id = msg.get('id', False)

            if msg_id and wa_id:
                self.msgid = msg_id
                return msg_id
            else:
                message = result.get('message', result)
                raise ValidationError(message)
        else:
            return super(QiscussMessage, self).message_send()

    def qc_message_check_allow_send(self, msgdata):
        ''' Check elapsed time '''
        self.ensure_one()
        # for rec in self:
        text_msg = msgdata.get('text')
        is_direct = msgdata.get('is_direct')
        if text_msg and len(text_msg) >= 4000:
            raise ValidationError(_('Message is to large (4.000 caracters).'))
        conversation_id = self.env['acrux.chat.conversation'].browse(msgdata.get('contact_id'))
        connector_id = conversation_id.connector_id
        app_id = connector_id.qc_app_name
        sdk_token = connector_id.apikey
        channel_id = connector_id.qc_channel_id
        data = {}
        header = {
            'Content-Type': 'application/json',
            'Qiscus-App-Id': app_id,
            'Qiscus-Secret-Key': sdk_token
        }
        param = {'wa_user_id': self.clean_number(self.contact_id.number), 'channel_id': channel_id}
        # try:
        data = connector_id.qc_request('post', 'api/v2/wa_sessions/show', param,
                              headers=header, timeout=20)
        if 'errors' in data and is_direct:
            if 'this room is not initiate any session yet' in str(data.get('errors')):
                raise ValidationError(_('%s. \nPlease send the default answer first and wait for your customer response.' % (
                    data.get('errors'))))
            #     #     data = self.automated_open_session(msgdata)
            #     #     time.sleep(10)
        # except Exception as e:
        #     pass

    def automated_open_session(self, msgdata):
        default_answer = self.env['acrux.chat.default.answer'].search([('name', '=', 'automated_msg')], limit=1)
        conversation_id = self.env['acrux.chat.conversation'].browse(msgdata.get('contact_id'))
        connector_id = conversation_id.connector_id
        payload = {'from_me': True, 'ttype': 'text', 'res_model': False, 'res_id': False, 'is_direct': False}
        template_obj = self.env['qiscus.template'].search([('name', 'ilike', 'chatroom_default_answer_text')], limit=1)
        payload.update({'contact_id': msgdata.get('contact_id'),
                        'template_id': template_obj.id,
                        })
        if default_answer:
            payload.update({'text': default_answer.text})
        else:
            payload.update({'text': 'Hey there...'})
        AcruxChatMessages = self.create(payload)
        headers = {}
        [message, path, header] = self.qc_ttype_automated_text(payload)
        headers['Qiscus-App-Id'] = connector_id.qc_app_name
        headers['Qiscus-Secret-Key'] = connector_id.apikey
        if header:
            headers.update(header)
        result = connector_id.qc_request('post', path, message, headers)

        whatsappID = result.get('contacts')
        for wa in whatsappID:
            wa_id = wa.get('wa_id', False)

        messageId = result.get('messages')
        for msg in messageId:
            msg_id = msg.get('id', False)

        if msg_id and wa_id:
            self.msgid = msg_id
            return msg_id
        else:
            message = result.get('message', result)
            raise ValidationError(message)
        return result

    def qc_ttype_automated_text(self, msgdata):
        conversation_id = self.env['acrux.chat.conversation'].browse(msgdata.get('contact_id'))
        template_obj = self.env['qiscus.template'].browse(msgdata.get('template_id'))
        connector_id = conversation_id.connector_id
        app_id = connector_id.qc_app_name
        channel_id = connector_id.qc_channel_id
        if not self.template_id:
            raise ValidationError('Template record does not exist or has been deleted')
        content_obj = self.env['qiscus.template.content'].search([('template_id', '=', int(msgdata.get('template_id')))], limit=1)
        template_content = content_obj.content
        count_var = len(re.findall(r'.[{{]\d[}}]+', template_content))
        pesan_text = '%s\n%s' % (conversation_id.name, msgdata.get('text'))
        messages = pesan_text.split('\n')
        count_message = 0
        message_obj = []
        for pesan in messages:
            message_obj.append({
                'type': 'text',
                'text': pesan
            })
            count_message += 1
        if count_message != count_var:
            raise ValidationError('Record does not match the specified template variable.')
        header = {'Content-Type': 'application/json'}
        ret = {
            'to': int(self.clean_number(conversation_id.number)),
            'recipient_type': 'individual',
            'type': 'template',
            'template': {
                'namespace': template_obj.namespace,
                'name': template_obj.name,
                'language': {
                    'policy': "deterministic",
                    'code': 'en'
                },
                'components': [{
                    'type': 'body',
                    'parameters': message_obj
                    # 'parameters': [{
                    #     'type': 'text',
                    #     'text': self.text
                    # }]
                }]
            }
        }
        return [ret, f'whatsapp/v1/{app_id}/{channel_id}/messages', header]

    @api.model
    def message_check_weight(self, field=None, value=None, raise_on=False):
        ''' Check size '''
        ret = super(QiscussMessage, self).message_check_weight(field=field, value=value, raise_on=raise_on)
        if self.contact_id.connector_id.connector_type == 'qiscuss':
            limit, msg = 5000000, '5 Mb'
            if self.user_has_groups('acrux_chat.group_chat_basic_extra'):
                limit, msg = 16000000, '16 Mb'
            if field:
                value = len(base64.b64decode(field) if field else b'')
            if (value or 0) >= limit:
                if raise_on:
                    raise ValidationError(_('Attachment exceeds the maximum size allowed (%s).') % msg)
                return False
        return ret
