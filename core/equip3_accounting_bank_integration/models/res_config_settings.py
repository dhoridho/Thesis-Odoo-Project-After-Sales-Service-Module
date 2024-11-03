from odoo import api, fields, models, _
import pytz, logging, requests, json
from odoo.exceptions import UserError, ValidationError
import sys, traceback


_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bank_integrate_url = fields.Char(
        string='Middleware URL', 
        related="company_id.bank_integrate_url",
        readonly=False,
    )
    bank_integrate_username = fields.Char(
        string='Username',
        related="company_id.bank_integrate_username",
        readonly=False,
    )
    bank_integrate_password = fields.Char(
        string='Password',
        related="company_id.bank_integrate_password",
        readonly=False,
    )
    validate_api = fields.Boolean(related="company_id.validate_api")


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            # 'bank_integrate_url': ICP.get_param('bank_integrate_url', False),
            # 'bank_integrate_username': ICP.get_param('bank_integrate_username', False),
            # 'bank_integrate_password': ICP.get_param('bank_integrate_password', False),
            # 'validate_api': ICP.get_param('validate_api', False),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ISP = self.env['ir.config_parameter'].sudo()
        # ISP.set_param('bank_integrate_url', self.env.company.bank_integrate_url)
        # ISP.set_param('bank_integrate_username', self.env.company.bank_integrate_username)
        # ISP.set_param('bank_integrate_password', self.env.company.bank_integrate_password)
        # ISP.set_param('validate_api', self.validate_api)

    def cek_bank_credential(self):
        domain = self.env.company.bank_integrate_url
        user = self.env.company.bank_integrate_username
        password = self.env.company.bank_integrate_password
        if domain and user and password:
            param_login = {
                          'email': user,
                          'password': password
                        }
            try:
                request_server_login = requests.post(f'{domain+"api/v1/login"}', params=param_login, headers=headers, verify=False)
                # request_server_login = requests.post(f'{domain+"api/v1/login"}', params=param_login, verify=True)
                response_login = json.loads(request_server_login.text)
                if request_server_login.status_code == 200:
                    self.env.company.validate_api = True
                    super(ResConfigSettings, self).set_values()
                    ISP = self.env['ir.config_parameter'].sudo()
                    # ISP.set_param('validate_api', self.validate_api)
                    res = super(ResConfigSettings, self).get_values()
                    ICP = self.env['ir.config_parameter'].sudo()
                    res.update({
                        'validate_api': self.env.company.validate_api,
                    })
                    return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'type': 'succes',
                                    'message': 'Succes',
                                    'next': {'type': 'ir.actions.act_window_close'},
                                    'sticky': False,
                                }
                            }
                else:
                    self.env.company.validate_api = False
                    if 'errors' in response_login:
                        text= str(response_login["message"]) + '\n'
                        for key, value in response_login["errors"].items():
                            text += str(key) + ' : ' + str(value) + '\n'
                        raise UserError(text)
                    raise UserError(response_login)
            except Exception as e:
                self.env.company.validate_api = False
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
        else: 
            self.env.company.validate_api = False