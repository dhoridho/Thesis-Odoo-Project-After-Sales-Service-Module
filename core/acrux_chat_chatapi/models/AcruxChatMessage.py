# -*- coding: utf-8 -*-
import base64
from werkzeug.utils import secure_filename
from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import formatLang
from odoo.addons.acrux_chat.tools import get_binary_attach


class AcruxChatMessage(models.Model):
    _inherit = 'acrux.chat.message'

    @api.model
    def ca_ttype_text(self):
        ret = {
            'phone': self.clean_number(self.contact_id.number),
            'body': self.text
        }
        return [ret, 'sendMessage']

    @api.model
    def ca_ttype_audio(self):
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        # Only suport 'audio/ogg; codecs=opusg'
        ret = {
            'phone': self.clean_number(self.contact_id.number),
        }
        if attach_id.mimetype == 'audio/ogg':
            # data:audio/ogg;base64,/9j/4AAQ...
            ret['audio'] = 'data:audio/ogg;base64,%s' % attach_id.datas.decode('ascii')
        else:
            # raise error ?
            ret['audio'] = url
        return [ret, 'sendPTT']

    @api.model
    def ca_ttype_file(self):
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        ret = {
            'phone': self.clean_number(self.contact_id.number),
            'caption': self.text or '',
            'filename': attach_id.name
        }
        if attach_id.mimetype:
            # data:image/jpeg;base64,/9j/4AAQ...
            ret['body'] = 'data:%s;base64,%s' % (attach_id.mimetype, attach_id.datas.decode('ascii'))
        else:
            ret['body'] = url
        return [ret, 'sendFile']

    @api.model
    def ca_ttype_product(self):
        url = content_str = False
        mimetype = filename = ''
        image_field = 'image_chat'  # to set dynamic: self.res_filed
        if not self.res_id or self.res_model != 'product.product':
            raise ValidationError('Product type is required.')
        prod_id = self.env[self.res_model].browse(self.res_id)
        if not prod_id:
            raise ValidationError('Product is required.')

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
                                       fields_ret=['mimetype', 'file_size'])
            size = attach and attach['file_size'] or len(base64.b64decode(content_str))
            mimetype = attach and attach['mimetype']
            if size:
                self.message_check_weight(value=size, raise_on=True)
            if mimetype:
                ext = mimetype.split('/')
                if len(ext) == 2:
                    filename = secure_filename('%s.%s' % (prod_id.name, ext[1]))
            else:
                prod_id, url = self.get_url_image(res_model=self.res_model, res_id=self.res_id,
                                                  field=image_field, prod_id=prod_id)
        # send ----------
        if not field_image or (not mimetype and not url):
            # Simple text message
            ret = {
                'phone': self.clean_number(self.contact_id.number),
                'body': caption
            }
            return [ret, 'sendMessage']
        else:
            ret = {
                'phone': self.clean_number(self.contact_id.number),
                'caption': caption,
                'filename': filename
            }
            if mimetype:
                # data:image/jpeg;base64,/9j/4AAQ...
                ret['body'] = 'data:%s;base64,%s' % (mimetype, content_str)
            elif url:
                ret['body'] = url
        return [ret, 'sendFile']

    @api.model
    def ca_ttype_sale(self):
        if self.res_model != 'sale.order':
            raise ValidationError('Order type is required.')
        return self.ca_ttype_file()

    @api.model
    def ca_ttype_location(self):
        ''' Text format:
                name
                address
                latitude, longitude
        '''
        parse = self.text.split('\n')
        if len(parse) != 3:
            return self.ca_ttype_text()
        cords = parse[2].split(',')
        ret = {
            'phone': self.clean_number(self.contact_id.number),
            'address': '%s\n%s' % (parse[0].strip(), parse[1].strip()),
            'lat': cords[0].strip('( '),
            'lng': cords[1].strip(') '),
        }
        return [ret, 'sendLocation']

    def message_parse(self):
        message = super(AcruxChatMessage, self).message_parse()
        connector_id = self.contact_id.connector_id
        if connector_id.connector_type == 'chatapi':
            if self.ttype == 'text':
                message = self.ca_ttype_text()
            elif self.ttype in ['image', 'video', 'file']:
                message = self.ca_ttype_file()
            elif self.ttype == 'audio':
                message = self.ca_ttype_audio()
            elif self.ttype == 'product':
                message = self.ca_ttype_product()
            elif self.ttype == 'sale_order':
                message = self.ca_ttype_sale()
            elif self.ttype == 'location':
                message = self.ca_ttype_location()
            elif self.ttype == 'contact':
                raise ValidationError('Not implemented')
        return message

    def message_send(self):
        ''' Call super at the beginning. '''
        ret = super(AcruxChatMessage, self).message_send()
        connector_id = self.contact_id.connector_id
        if connector_id.connector_type == 'chatapi' and not self.ttype.startswith('info'):
            [message, path] = self.message_parse()
            result = connector_id.ca_request('post', path, message)
            # "sent": true,
            # "id": "false_17472822486@c.us_DF38E6A25B42CC8CCE57EC40F",
            # "message": "ok"
            status = result.get('sent', False)
            messageId = result.get('id', False)
            if messageId and status:
                self.msgid = messageId
                return messageId
            else:
                message = result.get('message', result)
                raise ValidationError(message)
        else:
            return ret

    def message_check_allow_send(self):
        ''' Check elapsed time '''
        super(AcruxChatMessage, self).message_check_allow_send()
        # no limit

    @api.model
    def message_check_weight(self, field=None, value=None, raise_on=False):
        ''' Check size '''
        ret = super(AcruxChatMessage, self).message_check_weight(field=field, value=value, raise_on=raise_on)
        if self.contact_id.connector_id.connector_type == 'chatapi':
            limit, msg = 2000000, '2 Mb'
            if self.user_has_groups('acrux_chat.group_chat_basic_extra'):
                limit, msg = 4000000, '4 Mb'
            if field:
                value = len(base64.b64decode(field) if field else b'')
            if (value or 0) >= limit:
                if raise_on:
                    raise ValidationError(_('Attachment exceeds the maximum size allowed (%s).') % msg)
                return False
        return ret
