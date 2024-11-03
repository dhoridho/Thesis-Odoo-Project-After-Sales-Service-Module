from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessDenied
import requests
import json


class UsersWizardLogin(models.TransientModel):
    ''' Partner required '''
    _name = 'res.users.qiscuss'
    _description = 'Res Users Qiscuss Access'

    user_id = fields.Many2one('res.users', string='User ID')
    email = fields.Char('Email', required=True)
    password = fields.Char('Password', required=True)

    def _default_user(self):
        return self.env['res.users'].search([('id', '=', self.env.user.id)], limit=1)

    @api.model
    def default_get(self, fields):
        res = super(UsersWizardLogin, self).default_get(fields)
        res.update({
            'email': self.env.user.qc_email,
            'password': self.env.user.qc_password
        })
        return res

    def submit_user_login(self):
        _context = self.env.context
        models = _context.get('active_model')
        users = self.env['res.users'].browse(self.env.user.id)
        connectors = self.env['acrux.chat.connector'].browse(_context.get('active_id', []))
        header = {
            'Content-Type': 'application/json'
        }
        payload = {'email': self.email,
                   'password': self.password
        }
        response_data_auth = connectors.qc_request('post', 'api/v1/auth', payload, header, timeout=40)
        # try:
        #     auth_user = requests.post(f'https://multichannel.qiscus.com/api/v1/auth', data=payload,verify=True)
        #     response_data_auth = json.loads(auth_user.content)
        # except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
        #     raise ValidationError('connection_error',
        #         _('The url that this service requested returned an error.'))
        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))

        users.sudo().write({
            'qc_email': self.email,
            'qc_password': self.password,
            'qc_token': response_data_auth['data']['user']['authentication_token'],
            'qc_avatar_url': response_data_auth['data']['user']['avatar_url']
        })
        connectors.write({
            'qc_sdk_token': response_data_auth['data']['details']['sdk_user']['token'],
            'qc_status': True,
            'qc_qr_code': False
        })
        message = 'All good!'
        detail = 'WhatsApp connects to your phone to sync messages. ' \
                 'To reduce data usage, connect your phone to Wi-Fi.'
        return self.env['acrux.chat.pop.message'].message(message, detail) if message else True
        # header = {'Qiscus-App-Id':app_id,
        #           'Authorization':response_data_auth['data']['user']['authentication_token']}
        #
        # print("This is submit login function")
