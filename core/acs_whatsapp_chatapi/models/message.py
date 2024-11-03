# -*- coding: utf-8 -*-
import time
import urllib
from urllib.request import Request, urlopen
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.tools.mimetypes import guess_mimetype
import mimetypes

import json
import requests
import base64

from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import format_datetime


class AcsWhatsAppMessage(models.Model):
    _inherit = 'acs.whatsapp.message'

    def send_whatsapp_message(self):
        for rec in self:            
            try:
                if rec.message_type=='message':
                    URL = "%s/instance%s/sendMessage?token=%s" % (rec.company_id.whatsapp_api_url, rec.company_id.whatsapp_api_instance,rec.company_id.whatsapp_api_token) 
                    message = {
                        "phone": rec.mobile,
                        "body": rec.message,
                    }
                elif rec.message_type in ['file', 'file_url']:
                    URL = "%s/instance%s/sendFile?token=%s" % (rec.company_id.whatsapp_api_url, rec.company_id.whatsapp_api_instance,rec.company_id.whatsapp_api_token)
                    if rec.message_type=='file_url':
                        file_body = rec.file_url

                        filename = rec.file_url.split('/')[-1].split('.')[0]
                        file_ext = '.' + rec.file_url.split('.')[-1]
                        file_name = filename + file_ext
                    else:
                        file_body = "data:" + rec.mimetype + ";base64," + (rec.file).decode('utf-8')
                        file_name = rec.file_name
                    message = {
                        "phone": rec.mobile,
                        "body": file_body,
                        "filename": file_name,
                    }
                
                else:
                    URL = "%s/instance%s/sendLink?token=%s" % (rec.company_id.whatsapp_api_url, rec.company_id.whatsapp_api_instance,rec.company_id.whatsapp_api_token)
                    link_data = base64.b64encode(requests.get(rec.link).content)
                    http_message = urlopen(Request(rec.link, headers={'User-Agent': 'Mozilla/5.0'})).info()
                    message = {
                        "title": rec.message or "link",
                        "phone": rec.mobile,
                        "body": rec.link,
                        "previewBase64": "data:"+ http_message.get_content_type() + ";base64," + link_data.decode('utf-8'),
                    }
                
                headers = {'Content-type': 'application/json'}
                reply = requests.post(URL, data=json.dumps(message), headers=headers)
                if rec.message_type=='message':
                    reply_data = reply.json()
                    if reply_data.get('error'):
                        rec.state = 'error'
                    else:
                        rec.state = 'sent'
                    rec.reply_data = reply_data
                else:
                    rec.reply_data = reply
                    if reply.status_code==200:
                        rec.state = 'sent'
                    else:
                        rec.state = 'error'
            except Exception as e:
                rec.state = 'error'
                rec.error_message = e


class ACSwhatsappMixin(models.AbstractModel):
    _inherit = "acs.whatsapp.mixin"

    def acs_whatsapp_chat_history(self, partner, mobile):
        mobile = mobile.replace(' ', '')
        mobile = mobile.replace('+', '')
        URL = "%s/instance%s/messagesHistory?token=%s&chatId=%s" % (self.env.user.company_id.whatsapp_api_url, self.env.user.company_id.whatsapp_api_instance,self.env.user.company_id.whatsapp_api_token, mobile + '@c.us') 
        try:
            headers = {'Content-type': 'application/json'}
            reply = requests.get(URL, headers=headers)
            reply_data = json.loads(reply.text)
        except Exception as e:
            raise UserError(_("Something went wrong with configuration, please contact your administrator."))

        data = ""
        for msg in reply_data.get('messages'):
            date_time = time.strftime(DTF, time.localtime(msg['time']))
            date_time = datetime.strptime(date_time, DTF)
            date_time = format_datetime(self.env, date_time, dt_format='medium')

            message = msg['body']
            if msg['type']=='location':
                lat_long = msg['body'].split(';')
                message = "https://maps.google.com/?q=%s,%s" % (lat_long[0], lat_long[1])
            
            if msg['fromMe']:
                data += _("<div class='acs-right-chat'> <span>%s</span>") %(message)
                data += _("<br/><span class='pull-right acs-chat-name'> %s - (%s) <span></div>")%(self.env.user.company_id.name,date_time)
            else:
                data += _("<div class='acs-left-chat'> <span>%s</span>") %(message)
                data += _("<br/><span class='pull-right acs-chat-name'> %s - (%s) <span></div>")%(partner.name,date_time)

            data += _("<br/>")

        wiz = self.env['acs.whatsapp.history'].create({
            'data': data
        })
        action = self.env["ir.actions.actions"]._for_xml_id("acs_whatsapp.action_acs_whatsapp_history")
        action['res_id'] = wiz.id
        return  action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: