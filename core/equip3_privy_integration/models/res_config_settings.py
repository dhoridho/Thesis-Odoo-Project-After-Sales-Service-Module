from odoo import api, fields, models, _
import pytz, logging, requests, json
from odoo.exceptions import UserError, ValidationError
import requests


_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': '*/*','Accept-Encoding':'gzip, deflate, br'}

class ResConfigSettingsPrivyIntegration(models.TransientModel):
    _inherit = 'res.config.settings'

    is_privy_integration = fields.Boolean(config_parameter='equip3_privy_integration.is_privy_integration',string="Privy Integration")
    privy_username = fields.Char(string='Username',config_parameter='equip3_privy_integration.privy_username')
    privy_password = fields.Char(string='Password',config_parameter='equip3_privy_integration.privy_password')
    validate_privy_success = fields.Boolean(config_parameter='equip3_privy_integration.validate_privy_success')
    validate_privy_fail= fields.Boolean(config_parameter='equip3_privy_integration.validate_privy_fail')
    privy_api_key = fields.Char(config_parameter='equip3_privy_integration.privy_api_key')
    privy_secret_key = fields.Char(config_parameter='equip3_privy_integration.privy_secret_key')
    privy_channel_id = fields.Char(config_parameter='equip3_privy_integration.privy_channel_id')
    privy_base_url = fields.Char(config_parameter='equip3_privy_integration.privy_base_url')
    privy_access_token = fields.Char(config_parameter='equip3_privy_integration.privy_access_token')
    privy_login_url_info = fields.Char(config_parameter='equip3_privy_integration.privy_login_url_info')
    privy_id = fields.Char(config_parameter='equip3_privy_integration.privy_id')
    privy_enterprise_token = fields.Char(config_parameter='equip3_privy_integration.privy_enterprise_token')

    
    
    def privy_check_credential(self):
        is_privy_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.is_privy_integration')
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        privy_username = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_username')
        privy_password = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_password')
        payload = {"client_id":privy_username,"client_secret":privy_password,"grant_type": "client_credentials"}
        if is_privy_integration:
            try:
                login = requests.post(privy_url + '/oauth2/api/v1/token',json=payload,headers=headers)
            except requests.exceptions.ConnectionError:
                raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
            if login.status_code == 201:
                response = json.loads(login.content)
                self.env["ir.config_parameter"].sudo().set_param('equip3_privy_integration.validate_privy_success', True)
                self.env["ir.config_parameter"].sudo().set_param('equip3_privy_integration.validate_privy_fail', False)
                self.env["ir.config_parameter"].sudo().set_param('equip3_privy_integration.privy_access_token', response['data']['access_token'])
            
            else:
                self.env["ir.config_parameter"].sudo().set_param('equip3_privy_integration.validate_privy_fail', True)
                self.env["ir.config_parameter"].sudo().set_param('equip3_privy_integration.validate_privy_success', False)
                
                
                
            
            
    
   