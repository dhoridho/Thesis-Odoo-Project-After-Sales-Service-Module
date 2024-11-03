from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessDenied, UserError
from cryptography.fernet import Fernet
import sys
import requests
import json
import logging
import base64
_logger = logging.getLogger(__name__)


class UsersWizardLogin(models.TransientModel):
    ''' Partner required '''
    _name = 'res.users.ceisa'
    _description = 'Res Users CEISA Access'

    user_id = fields.Many2one('res.users', string='User ID')
    username = fields.Char('Username', required=True)
    password = fields.Char('Password', required=True)
    message = fields.Text('Message')
    userkey = fields.Char('UserKey')

    @api.model
    def default_get(self, fields):
        res = super(UsersWizardLogin, self).default_get(fields)
        _context = self.env.context
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        username = company.ceisa_user
        password = company.ceisa_password
        user_key = company.ceisa_user_key
        if username and password:
            if user_key:
                hmpass = self._decrypt(password, user_key)
        else:
            hmpass = False
            user_key = False

        if _context.get('error_message'):
            res.update({
                'message': _context.get('error_message'),
                'username': username,
                'password': hmpass,
                'userkey': user_key
            })
        else:
            res.update({
                'username': username,
                'password': hmpass,
                # 'userkey': user_key
            })
        return res

    @api.model
    def create(self, vals):
        if 'password' in vals:
            # password = vals.get('password')
            # vals['password'] = base64.b64encode(password.encode("UTF-8"))
            if 'userkey' in vals:
                password, ukey = self._encrypt(vals.get('password'), vals.get('userkey'))
            else:
                password, ukey = self._encrypt(vals.get('password'))
            vals['password'] = password
            vals['userkey'] = ukey
        result = super(UsersWizardLogin, self).create(vals)
        return result

    def write(self, vals):
        if 'password' in vals:
            # password = vals.get('password')
            # vals['password'] = base64.b64encode(password.encode("UTF-8"))
            if 'userkey' in vals:
                password, ukey = self._encrypt(vals.get('password'), vals.get('userkey'))
            else:
                password, ukey = self._encrypt(vals.get('password'))
            vals['password'] = password
            vals['userkey'] = ukey
        result = super(UsersWizardLogin, self).write(vals)
        return result

    def submit_user_login(self):
        _context = self.env.context
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        models_id = self._context.get('active_id', False)
        if not models_id:
            raise UserError(
                _("Programming error: wizard action executed without active_ids in context."))

        if self.env.context['active_model'] == 'ceisa.export.documents':
            ceisa_documents = self.env['ceisa.export.documents'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc23':
            ceisa_documents = self.env['ceisa.documents.bc23'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc25':
            ceisa_documents = self.env['ceisa.documents.bc25'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc261':
            ceisa_documents = self.env['ceisa.documents.bc261'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc262':
            ceisa_documents = self.env['ceisa.documents.bc262'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc27':
            ceisa_documents = self.env['ceisa.documents.bc27'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc40':
            ceisa_documents = self.env['ceisa.documents.bc40'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc41':
            ceisa_documents = self.env['ceisa.documents.bc41'].browse(models_id)
        else:
            ceisa_documents = self.env['ceisa.import.documents'].browse(models_id)
        users = self.env['res.users'].browse(self.env.user.id)
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        # password = self.password
        # ukey = self.userkey
        password = self._decrypt(self.password, self.userkey)
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }

        payload = {'username': self.username,
                   'password': password
        }
        data = json.dumps(payload)
        response_data_auth = []
        try:
            auth_user = requests.post(f'%s/auth-amws/v1/user/login' % url, data=data, headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(auth_user.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'login error' in response_data_auth['status']:
            # raise ValidationError('%s' % (response_data_auth['message']))
            raise UserError('Username or password is incorrect. Please check your setting!')
        elif 'Exception' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['Exception']))
        else:
            company.sudo().write({
                'ceisa_user': self.username,
                # 'ceisa_password': str(base64.b64encode(password.encode("UTF-8"))),
                'ceisa_password': self.password,
                'ceisa_user_key': self.userkey,
                'ceisa_token': response_data_auth['item']['access_token'],
                'ceisa_refresh_token': response_data_auth['item']['refresh_token'],
                'ceisa_id_token': response_data_auth['item']['id_token'],
                'ceisa_token_type': response_data_auth['item']['token_type'],
                'ceisa_status': True
            })
            if _context.get('default_path_target') == 'ndpbm':
                ceisa_documents.update_ndpbm()
            elif _context.get('default_path_target') == 'storehouse_location':
                ceisa_documents.update_storehouse_location()
            elif _context.get('default_path_target') == 'origin_port':
                ceisa_documents.update_origin_port_export()
            elif _context.get('default_path_target') == 'port_by_country':
                ceisa_documents.update_export_destination_port_by_country()
            # elif _context.get('default_path_target') == 'master_data':
            #     ceisa_documents.action_get_master_data()
            elif _context.get('default_path_target') == 'refresh_token':
                return response_data_auth['item']['access_token']
            else:
                ceisa_documents.send_document(response_data_auth['item']['access_token'])
        return response_data_auth

    def log_request_error(param, req=None):
        try:
            param = json.dumps(param, indent=4, sort_keys=True, ensure_ascii=False)[:1000]
            if req is not None:
                _logger.error('\nSTATUS: %s\nSEND: %s\nRESULT: %s' %
                              (req.status_code, req.request.headers, req.text and req.text[:1000]))
        except Exception as _e:
            pass
        _logger.error(param, exc_info=True)

    def _encrypt(self, password, key=False):
        if key:
            ukey = bytes(key, 'UTF-8')
        else:
            ukey = Fernet.generate_key()
        fernet = Fernet(ukey)
        encMessage = fernet.encrypt(password.encode())
        return str(encMessage, 'UTF-8'), str(ukey, 'UTF-8')

    def _decrypt(self, password, key=False):
        if key:
            ukey = bytes(key, 'UTF-8')
        else:
            ukey = Fernet.generate_key()
        fernet = Fernet(ukey)
        upass = bytes(password, 'UTF-8')
        decMessage = fernet.decrypt(upass).decode()
        return decMessage