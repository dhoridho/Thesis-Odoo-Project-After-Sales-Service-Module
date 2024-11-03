# -*- coding: utf-8 -*-
import sys
import requests
import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.addons.acrux_chat.tools import TIMEOUT, log_request_error, get_image_from_url


class AcruxChatConnector(models.Model):
    _inherit = 'acrux.chat.connector'

    connector_type = fields.Selection(selection_add=[('chatapi', 'ChatApi')],
                                      ondelete={'chatapi': 'cascade'})
    ca_app_name = fields.Char('App Instance')
    ca_status = fields.Boolean('Connected', default=False)
    ca_status_txt = fields.Char('Status')
    ca_qr_code = fields.Binary('QR Code')

    @api.onchange('connector_type', 'endpoint')
    def _onchange_chatapi(self):
        if self.connector_type == 'chatapi':
            self.time_to_respond = False
            if self.endpoint:
                _url, _instance, ca_app_name = self.endpoint.partition('instance')
                self.ca_app_name = ca_app_name and ca_app_name.rstrip('/ ')
            else:
                self.ca_app_name = False

    def ca_get_endpoint(self, resource_path):
        return '%s/%s?token=%s' % (self.endpoint.strip('/'), resource_path, self.apikey)

    def ca_set_settings(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if '//localhost/' in base_url:
            raise ValidationError('Not set in Local Server (localhost).')
        if not self.uuid:
            raise ValidationError('Set first Unique identifier.')
        webhookUrl = '%s/acrux_webhook/chatapi/%s' % (base_url.rstrip('/ '), self.uuid.strip())
        param = {'webhookUrl': webhookUrl,
                 'ackNotificationsOn': False,
                 'ignoreOldMessages': True,
                 'chatUpdateOn': True}
        data = self.ca_request('post', 'settings', param)
        data = data or {}
        updated = data.get('updated', {}).get('webhookUrl', '1')
        new_webhookUrl = data.get('webhookUrl', '2')
        if updated != new_webhookUrl:
            raise ValidationError('Error setting Webhook URL.')
        message = 'All good!'
        detail = 'Webhook URL updated.'
        return self.env['acrux.chat.pop.message'].message(message, detail)

    def ca_get_settings(self):
        '''
        webhookUrl - Http or https URL for receiving notifications. For testing, we recommend using our RequestBin.
        ackNotificationsOn - Turn on/off ack (message delivered and message viewed) notifications in webhooks. GET method works for the same address.
        chatUpdateOn - Turn on/off chat update notifications in webhooks. GET method works for the same address.
        videoUploadOn - Turn on/off receiving video messages.
        proxy - Socks5 IP address and port proxy for instance.
        guaranteedHooks - Guarantee webhook delivery. Each webhook will make 20 attempts to send until it receives 200 status from the server.
        ignoreOldMessages - Do not send webhooks with old messages during authorization.
        processArchive - Process messages from archived chats.
        instanceStatuses - Turn on/off collecting instance status changing history.
        webhookStatuses - Turn on/off collecting messages webhooks statuses.
        statusNotificationsOn - Turn on/off instance changind status notifications in webhooks.
        '''
        data = self.ca_request('get', 'settings')
        message = 'Chat-Api Settings:'
        detail = json.dumps(data, indent=0).replace('{', '').replace('}', '').replace('"', '').replace('\n', '<br/>')
        return self.env['acrux.chat.pop.message'].message(message, detail.strip())

    def ca_get_chat_list(self):
        self.ensure_one()
        ''' The chat list includes avatars. '''
        data = self.ca_request('get', 'dialogs')
        dialogs = data.get('dialogs', [])
        vals = {}
        for user in dialogs:
            phone = '+' + user.get('id', '').split('@')[0]
            name = user.get('name', '')
            image_url = user.get('image', '')
            vals[phone] = {'name': name, 'image_url': image_url}
        Conversation = self.env['acrux.chat.conversation']
        ''' Search in conversations of all connector ! '''
        for conv in Conversation.search([('image_128', '=', False)]):
            if conv.number in vals:
                image_url = vals[conv.number].get('image_url', '')
                if image_url and image_url.startswith('http'):
                    raw_image = get_image_from_url(image_url)
                    conv.image_128 = raw_image

    def ca_set_logout(self):
        message = detail = False
        data = self.ca_request('post', 'logout', timeout=40)
        result = data.get('result')
        if result:
            self.ca_status = False
            self.ca_qr_code = False
            message = 'Wait a minute and try again to get your QR Code.'
        return self.env['acrux.chat.pop.message'].message(message, detail) if message else True

    def ca_get_status(self):
        ''' accountStatus: [ got qr code, authenticated, loading, init, not_paid ]
            no_wakeup: auto init '''
        message = detail = False
        param = {'full': True, 'no_wakeup': False}  # default: False - False
        data = self.ca_request('get', 'status', param, timeout=40)
        status = data.get('accountStatus')
        qrCode = data.get('qrCode')
        if status == 'authenticated':
            self.ca_status = True
            self.ca_qr_code = False
            message = 'All good!'
            detail = 'WhatsApp connects to your phone to sync messages. ' \
                     'To reduce data usage, connect your phone to Wi-Fi.'
            self.ca_set_settings()
        elif status == 'got qr code':
            if qrCode:
                self.ca_qr_code = qrCode.split('base64,')[1]
            else:
                self.ca_qr_code = False
                message = 'An unexpected error occurred. ' \
                          'Login to your Chta-api account and get the QR Code from there.'
            self.ca_status = False
        else:
            self.ca_status = False
            statusData = data.get('statusData')
            title = statusData.get('title')
            msg = statusData.get('msg')
            substatus = statusData.get('substatus')
            message = 'Status: %s' % (substatus or '-')
            detail = '<b>%s</b><br/>%s' % (title, msg)
        return self.env['acrux.chat.pop.message'].message(message, detail) if message else True

    def ca_request(self, req_type, path, param={}, timeout=False):
        def response_handle_error(req):
            error = False
            try:
                ret = req.json()
            except ValueError as _e:
                ret = {}
            err = ret.get('error', 'Send Error')
            message = ret.get('message', 'Send Error')
            if req.status_code == 401:
                error = err
            elif not 200 <= req.status_code <= 299:
                error = err or message
            if error:
                log_request_error([error, req_type, path, param], req)
                raise ValidationError(error)
            return ret
        self.ensure_one()
        result = {}
        timeout = timeout or TIMEOUT
        url = self.ca_get_endpoint(path)
        header = {'Accept': 'application/json'}
        req = False
        try:
            if req_type == 'post':
                data = json.dumps(param)
                header.update({'Content-Type': 'application/json'})
                w = len(data) / 20000
                timeout = (int(max(10, w)), 20)
                req = requests.post(url, data=data, headers=header, timeout=timeout, verify=self.verify)
                result = response_handle_error(req)
            elif req_type == 'get':
                if path == 'qr_code':
                    header = {'Accept': 'image/png', 'Content-Type': 'application/json'}
                req = requests.get(url, params=param, headers=header, timeout=timeout, verify=self.verify)
                result = response_handle_error(req)
        except requests.exceptions.SSLError as _err:
            log_request_error(['SSLError', req_type, path, param])
            raise UserError(_('Error! Could not connect to Chat-Api server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            log_request_error(['ConnectTimeout', req_type, path, param])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            log_request_error(['requests', req_type, path, param])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Chat-Api account.\n%s') % ex_type)
        self.print_result(req_type, url, result, param, req)
        return result

    def print_result(self, req_type, url, result, param, req):
        try:
            Host = request.httprequest.headers.get('Host')
            if Host.startswith('localhost'):
                print('status =', req and req.status_code or 'except request')
                print(request.httprequest.headers)
                print('%%%% => %s %s' % (req_type.upper(), url))
                if param:
                    body = param.get('body', False)
                    if body:
                        param['body'] = body[0:100]
                    data = json.dumps(param, indent=2, sort_keys=True)
                    data = data.replace('\\"', "'")
                    print(data)
                print('################ resultado')
                data = json.dumps(result, indent=2, sort_keys=True)
                print(data)
        except RuntimeError:
           pass

