from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from .tools import hdencrypt, hddecrypt, log_request_error
import sys
import json
import requests
import logging
_logger = logging.getLogger(__name__)


class CeisaResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Resource Config Settings'


    ceisa_user = fields.Char('CEISA User',
                             related='company_id.ceisa_user', readonly=False)
    ceisa_password = fields.Char('CEISA Password',
                                 related='company_id.ceisa_password', readonly=False)
    ceisa_user_key = fields.Char('CEISA User Key',
                                 related='company_id.ceisa_user_key', readonly=False)
    # ceisa_user_iv = fields.Char('CEISA User Initialization')
    ceisa_user_token = fields.Char('CEISA User Token',
                                   related='company_id.ceisa_user_token', readonly=False)

    @api.model
    def get_values(self):
        res = super(CeisaResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        # userpass = ICP.get_param('ceisa_password', False)
        # userkey = ICP.get_param('ceisa_user_key', False)
        company = self.env.company
        userpass = company.ceisa_password
        userkey = company.ceisa_user_key
        if userpass and userkey:
            try:
                password = hddecrypt(userpass, userkey)
            except Exception as _e:
                password = userpass
                pass
        else:
            password = False
        # res.update({'ceisa_user': ICP.get_param('ceisa_user', False),
        #             'ceisa_password': password,
        #             })
        res.update({'ceisa_user': company.ceisa_user,
                    'ceisa_password': password,
                    'ceisa_user_key': userkey
                    })
        return res

    def set_values(self):
        super(CeisaResConfigSettings, self).set_values()
        if self.ceisa_password:
            password, passukey = hdencrypt(self.ceisa_password)
        else:
            password, passukey = None, None
        self.company_id.sudo().update({'ceisa_user': self.ceisa_user,
                                       'ceisa_password': password,
                                       'ceisa_user_key': passukey
                                       })
        # ISP = self.env['ir.config_parameter'].sudo()
        # ISP.set_param('ceisa_user', self.ceisa_user)
        # ISP.set_param('ceisa_password', password)
        # ISP.set_param('ceisa_user_key', passukey)

    def action_submit_ceisa_user(self):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        login_path = self.env['ir.config_parameter'].get_param('ceisa.login.path.api.url')
        # company = self.env['res.company'].browse(self.env.user.company_id.id)
        # ceisa_user = self.env['ir.config_parameter'].get_param('ceisa_user')
        # ceisa_password = self.env['ir.config_parameter'].get_param('ceisa_password')
        # ceisa_user_key = self.env['ir.config_parameter'].get_param('ceisa_user_key')
        # ceisa_user = self.ceisa_user
        # ceisa_password = self.ceisa_password
        # ceisa_user_key = self.env.company.ceisa_user_key
        # if ceisa_password and ceisa_user_key:
        #     password = hddecrypt(ceisa_password, ceisa_user_key)
        # else:
        #     password = None

        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }
        if self.ceisa_user and self.ceisa_password:
            payload = {'username': self.ceisa_user,
                       'password': self.ceisa_password
            }
        else:
            raise UserError('Username or password is required. Please check your setting!')
        data = json.dumps(payload)
        response_data_auth = []
        try:
            auth_user = requests.post(f'%s/%s' % (url, login_path), data=data, headers=header, timeout=40,
                                      verify=True)
            response_data_auth = json.loads(auth_user.content)
        except requests.exceptions.SSLError as _err:
            log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)
        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'login error' in response_data_auth['status']:
            # raise ValidationError('%s' % (response_data_auth['message']))
            raise UserError('Username or password is incorrect. Please check your setting!')
        elif 'Exception' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['Exception']))
        elif 'status' in response_data_auth and 'success' in response_data_auth['status']:
            title = 'Message:'
            msg = response_data_auth['message']
            substatus = response_data_auth['status']
            message = 'Status: %s' % (substatus or '-')
            detail = '<b>%s</b><br/>%s' % (title, msg)
            # raise ValidationError('%s' % (response_data_auth['message']))
            if 'item' in response_data_auth:
                if response_data_auth['item'] == None:
                    # ISP.set_param('ceisa_status', False)
                    raise ValidationError('Null data from the Server response. Please contact your Administrator!')
                else:
                    # ISP = self.env['ir.config_parameter'].sudo()
                    # ISP.set_param('ceisa_user_token', response_data_auth['item']['access_token'])
                    self.company_id.sudo().update({'ceisa_user_token': response_data_auth['item']['access_token']})
            return self.env['ceisa.pop.message'].message(message, detail) if message else True
        return response_data_auth
