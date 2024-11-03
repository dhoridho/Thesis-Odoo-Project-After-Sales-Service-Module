# -*- coding: utf-8 -*-
import sys
import requests
import json
import http.client
from urllib.parse import urlparse
from werkzeug.urls import url_join
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
from odoo.addons.acrux_chat.tools import TIMEOUT, log_request_error, get_image_from_url

API3_ENDPOINT = "https://api3.qiscus.com/api/v2/sdk/"
API_MULTICHANNEL = "https://multichannel-api.qiscus.com/"


class QiscussConnector(models.Model):
    _inherit = 'acrux.chat.connector'

    connector_type = fields.Selection(selection='_get_new_connector_type', string='Connect to',
                                      ondelete={'qiscuss': 'cascade'},
                                      default='qiscuss', required=True,
                                      help='Type for connector, every new connector has to add its own type')
    qc_app_name = fields.Char('App ID')
    qc_status = fields.Boolean('Connected', default=False)
    qc_status_txt = fields.Char('Status')
    qc_qr_code = fields.Binary('QR Code')
    qc_channel = fields.Selection([('wa', 'Whatsapp')],
                                  string='Channel', required=True, default='wa')
    qc_channel_id = fields.Char('Channel ID')
    qc_sdk_token = fields.Char('SDK Token')
    qc_template_ids = fields.One2many('qiscus.template', 'connector_id', string='Templates')
    qc_webhook_url = fields.Char('Webhook URL', readonly=True)
    connection_status = fields.Selection([('connect', 'Connected'), ('disconnect', 'Disconnected')],
                                         compute="_compute_connection_status", string='Status', store=False)

    _sql_constraints = [
        ('channel_uniq', 'CHECK(1=1)', _('Channel ID must be unique.')),
        ('api_uniq', 'CHECK(1=1)', _('API URL must be unique.')),
        ('key_uniq', 'CHECK(1=1)', _('Access Key must be unique.')),
    ]

    def _compute_connection_status(self):
        for record in self:
            if record.qc_status:
                record.connection_status = "connect"
            else:
                record.connection_status = "disconnect"

    @api.constrains('qc_channel_id', 'endpoint', 'apikey')
    def _check_unique_record(self):
        for record in self:
            check_record = self.search(
                [('endpoint', '=', record.endpoint), ('apikey', '=', record.apikey), ('id', '!=', record.id)], limit=1)
            if check_record:
                check_channel_record = self.search([('endpoint', '=', record.endpoint), ('apikey', '=', record.apikey),
                                                    ('qc_channel_id', '=', record.qc_channel_id),
                                                    ('id', '!=', record.id)], limit=1)
                if check_channel_record:
                    raise ValidationError("Record Already Exist with Channel, Api URL, Access Key.")

    @api.model
    def _get_new_connector_type(self):
        # selection = [
        #     ('generic', 'Generic'), ('qiscuss', 'Qiscuss')
        # ]
        selection = [
            ('qiscuss', 'Qiscuss')
        ]
        return selection

    @api.onchange('connector_type', 'endpoint')
    def _onchange_qiscuss(self):
        if self.connector_type == 'qiscuss':
            self.time_to_respond = False
            # if self.endpoint:
            #     _url, _instance, qc_app_name = self.endpoint.partition('instance')
            #     self.qc_app_name = qc_app_name and qc_app_name.rstrip('/ ')
            # else:
            #     self.qc_app_name = False

    @api.onchange('qc_app_name')
    def _onchange_appid(self):
        if self.connector_type == 'qiscuss':
            self.uuid = self.qc_app_name

    # def qc_get_endpoint(self, resource_path):
    #     return '%s/%s?token=%s' % (self.endpoint.strip('/'), resource_path, self.apikey)
    def qc_get_endpoint(self, resource_path, api_url=None):
        if api_url:
            return '%s/%s' % (api_url.strip('/'), resource_path)
        else:
            return '%s/%s' % (self.endpoint.strip('/'), resource_path)

    def check_url(self, url):
        url = urlparse(url)
        conn = http.client.HTTPConnection(url.netloc)
        conn.request('HEAD', url.path)
        try:
            if conn.getresponse():
                return True
        except RuntimeError:
            pass
        return False

    def qc_set_settings(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        hostname = base_url.split('//')[1]
        secure_base_url = url_join('https:', '//' + hostname)
        if self.check_url(secure_base_url):
            used_url = secure_base_url
        else:
            used_url = base_url

        self.uuid = self.qc_channel_id
        if '//localhost/' in base_url:
            raise ValidationError('Not set in Local Server (localhost).')
        if not self.uuid:
            raise ValidationError('Set first Unique identifier.')
        # webhookUrl = '%s/qiscuss_webhook/wa/%s' % (base_url.rstrip('/ '), self.uuid.strip())
        webhookUrl = '%s/qiscuss_webhook/wa/%s' % (used_url.rstrip('/ '), self.uuid.strip())
        param = {'webhooks': {
            'url': webhookUrl
        }
        }
        app_id = self.qc_app_name
        channel_id = self.qc_channel_id
        header = {
            'Content-Type': 'application/json',
            'Qiscus-App-Id': app_id,
            'Qiscus-Secret-Key': self.apikey
        }
        data = self.qc_request('post', f'whatsapp/{app_id}/{channel_id}/settings', param, headers=header)
        data = data or {}
        # updated = data.get('updated', {}).get('webhookUrl', '1')
        # new_webhookUrl = data.get('webhookUrl', '2')
        # if updated != new_webhookUrl:
        #     raise ValidationError('Error setting Webhook URL.')
        self.qc_webhook_url = webhookUrl
        message = 'All good!'
        detail = 'Webhook URL updated.'
        # Trigger cron for active if cron not active
        syncron = self.env['ir.cron'].sudo().search(
            [('name', '=', 'Qiscus Conversation Syncronize Scheduler'), ('active', '=', False)])
        if syncron:
            syncron.sudo().write({'active': True})
        return self.env['acrux.chat.pop.message'].message(message, detail)

    def qc_get_settings(self):
        app_id = self.qc_app_name
        channel_id = self.qc_channel_id
        header = {
            'Qiscus-App-Id': app_id,
            'Qiscus-Secret-Key': self.apikey
        }
        data = self.qc_request('get', f'whatsapp/{app_id}/{channel_id}/settings', headers=header)
        message = 'Qiscuss Settings:'
        detail = json.dumps(data, indent=0).replace('{', '').replace('}', '').replace('"', '').replace('\n', '<br/>')
        return self.env['acrux.chat.pop.message'].message(message, detail.strip())

    def qc_get_chat_list(self):
        self.ensure_one()
        ''' The chat list includes avatars. '''
        app_id = self.qc_app_name
        sdk_token = self.qc_sdk_token
        header = {
            'Qiscus-Sdk-App-Id': app_id,
            'Qiscus-Sdk-Token': sdk_token
        }
        # data = self.qc_request('get', 'dialogs')
        data = self.qc_request('get', 'user_rooms?page=1&show_participants=true&limit=50&room_type=default',
                               headers=header, timeout=20, api_url=API3_ENDPOINT)
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

    def qc_get_templates(self):
        self.ensure_one()
        app_id = self.qc_app_name
        channel_id = self.qc_channel_id
        header = {'Qiscus-App-Id': app_id,
                  'Authorization': self.env.user.qc_token}
        param = {'approved': True,
                 'limit': 1000,
                 'channel_id': channel_id}
        response_data = self.qc_request('get', 'api/v2/admin/hsm', param, headers=header, timeout=40)
        if response_data['data']['hsm_templates']:

            ids = [data['id'] for data in response_data['data']['hsm_templates']]
            qiscus_template_to_delete = self.env['qiscus.template'].search(
                ['|', ('qiscus_template_id', 'not in', ids), ('connector_id', '=', False)])
            if qiscus_template_to_delete and len(qiscus_template_to_delete) > 0:
                for unlink_data in qiscus_template_to_delete:
                    unlink_data.unlink()
            qc_template_ids = []
            for data in response_data['data']['hsm_templates']:
                qiscus_template = self.env['qiscus.template'].search(
                    [('qiscus_template_id', '=', int(data['id'])), ('connector_id', '=', self.id)])
                if not qiscus_template:
                    line_ids = []
                    # template_to_create = self.create(
                    #     {'qiscus_template_id': data['id'], 'name': data['name'], 'namespace': data['namespace']})
                    for line in data['hsm_details']:
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        line_ids.append((0, 0, {'language': line['language'],
                                                'content': f"""{header}{header_content}{line['content']}\n{footer_content}""",
                                                'content_id': line['id'],
                                                }))
                    qc_template_ids.append((0, 0, {
                        'qiscus_template_id': int(data['id']),
                        'name': data['name'],
                        'namespace': data['namespace'],
                        'content_ids': line_ids,
                        'connector_id': self.id
                    }))
                else:
                    line_ids = []
                    for line in data['hsm_details']:
                        qiscus_template_content = self.env['qiscus.template.content'].sudo().search(
                            [('template_id', '=', qiscus_template.id), ('content_id', '=', line['id'])])
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        if qiscus_template_content:
                            # qiscus_template_content.language =  line['language']
                            # qiscus_template_content.content =  f"""{header}{header_content}{line['content']}\n{footer_content}"""
                            qiscus_template_content.write({
                                'language': line['language'],
                                'content': f"""{header}{header_content}{line['content']}\n{footer_content}"""
                            })
                        else:
                            line_ids.append((0, 0, {'content_id': line['id'],
                                                    'language': line['language'],
                                                    'content': f"""{header}{header_content}{line['content']}\n{footer_content}"""
                                                    }))
                    # qiscus_template.content_ids = line_ids
                    qiscus_template.write({
                        'name': data['name'],
                        'namespace': data['namespace'],
                        'content_ids': line_ids
                    })
                    # qc_template_ids.append((6, 0, qiscus_template.ids))
                ids_to_delete = [data_delete['id'] for data_delete in data['hsm_details']]
                qiscus_template_content_delete = self.env['qiscus.template.content'].sudo().search(
                    [('template_id', '=', qiscus_template.id), ('content_id', 'not in', ids_to_delete)])
                if qiscus_template_content_delete and len(qiscus_template_content_delete) > 0:
                    for delete in qiscus_template_content_delete:
                        delete.unlink()
            self.qc_template_ids = qc_template_ids

    def qc_set_logout(self):
        message = detail = False
        headers = {
            'Content-Type': 'application/json',
            'app_id': self.qc_app_name,
            'authorization': self.env.user.qc_token,
            'qiscus-app-id': self.qc_app_name
        }
        data = self.qc_request('post', 'api/v1/auth/logout', headers=headers, timeout=40)
        result = data.get('data')
        if result:
            self.qc_status = False
            self.qc_qr_code = False
            # message = 'Wait a minute and try again to get your QR Code.'
            message = 'Logout Success.'
        return self.env['acrux.chat.pop.message'].message(message, detail) if message else True

    def qc_get_status(self):
        ''' accountStatus: [ got qr code, authenticated, loading, init, not_paid ]
            no_wakeup: auto init '''
        message = detail = False
        self.qc_set_settings()
        if self.env.user.qc_email and self.qc_status:
            header = {
                'Content-Type': 'application/json'
            }
            payload = {'email': self.env.user.qc_email,
                       'password': self.env.user.qc_password
                       }
            response_data_auth = self.qc_request('post', 'api/v1/auth', payload, header, timeout=40)
            if 'errors' in response_data_auth:
                self.qc_status = False
                raise ValidationError('%s' % (response_data_auth['errors']))
            users = self.env['res.users'].browse(self.env.user.id)
            users.sudo().write({
                'qc_token': response_data_auth['data']['user']['authentication_token'],
                'qc_avatar_url': response_data_auth['data']['user']['avatar_url']
            })
            self.qc_sdk_token = response_data_auth['data']['details']['sdk_user']['token']
            self.qc_status = True
            self.qc_qr_code = False
            message = 'All good!'
            detail = 'WhatsApp connects to your phone to sync messages. ' \
                     'To reduce data usage, connect your phone to Wi-Fi.'
            return self.env['acrux.chat.pop.message'].message(message, detail) if message else True
        else:
            return {
                'name': 'User Login to Qiscus',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users.qiscuss',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
            }

    def qc_request(self, req_type, path, param={}, headers=False, timeout=False, api_url=None):
        def response_handle_error(req):
            error = False
            try:
                ret = req.json()
            except ValueError as _e:
                ret = {}
            # err = ret.get('error', 'Send Error')
            err = ret.get('errors', 'Send Error')
            message = ret.get('message', 'Send Error')
            if req.status_code == 401:
                error = err
            elif not 200 <= req.status_code <= 299:
                error = err or message
            if error:
                log_request_error([error, req_type, path, param], req)
                # raise ValidationError(error)
            return ret

        self.ensure_one()
        result = {}
        timeout = timeout or TIMEOUT
        if api_url:
            url = self.qc_get_endpoint(path, api_url)
        else:
            url = self.qc_get_endpoint(path)
        header = {'Accept': 'application/json'}
        req = False
        try:
            if headers:
                header.update(headers)
            if req_type == 'post':
                data = json.dumps(param)
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
            raise UserError(_('Error! Could not connect to Qiscus server. '
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
            raise UserError(_('Error! Could not connect to Qiscus account.\n%s') % ex_type)
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
                    # print(data)
                print('################ result')
                data = json.dumps(result, indent=2, sort_keys=True)
                print(data)
        except RuntimeError:
            pass

