from odoo import api, fields, models, _
import pytz, logging, requests, json
from odoo.exceptions import UserError, ValidationError
import requests


_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': '*/*','Accept-Encoding':'gzip, deflate, br'}

class ResConfigSettingsAccountingEfaktur(models.TransientModel):
    _inherit = 'res.config.settings'

    is_eva_job_portal_integration = fields.Boolean(config_parameter='equip3_eva_jobportal_integration.is_eva_job_portal_integration',string="Eva Job Portal Integration")
    eva_job_portal_url = fields.Char(string='URL',config_parameter='equip3_eva_jobportal_integration.eva_job_portal_url')
    eva_job_portal_username = fields.Char(string='Username',config_parameter='equip3_eva_jobportal_integration.eva_job_portal_username')
    eva_job_portal_password = fields.Char(string='Password',config_parameter='equip3_eva_jobportal_integration.eva_job_portal_password')
    validate_api_eva_first = fields.Boolean(config_parameter='equip3_eva_jobportal_integration.validate_api_first')
    validate_api_eva_job_portal = fields.Boolean(config_parameter='equip3_eva_jobportal_integration.validate_api_eva_job_portal')
    validate_eva_job_portal_fail = fields.Boolean(config_parameter='equip3_eva_jobportal_integration.validate_eva_job_portal_fail')
    eva_job_portal_token = fields.Char(config_parameter='equip3_eva_jobportal_integration.eva_job_portal_token')
    login_url_info = fields.Char(config_parameter='equip3_eva_jobportal_integration.login_url_info')

    
    
    def cek_eva_job_portal_credential(self):
        is_eva_job_portal_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.is_eva_job_portal_integration')
        eva_job_portal_url = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_url')
        eva_job_portal_username = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_username')
        eva_job_portal_password = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_password')
        payload = {"email":eva_job_portal_username,"password":eva_job_portal_password}
        if is_eva_job_portal_integration:
        
            try:
                login = requests.post(eva_job_portal_url + '/api/v1/auth/login',json=payload,headers=headers)
                if login.status_code == 200:
                    response = json.loads(login.content)
                    # print("hereeee")
                    # print(response['data']['token'])
                    # print(response['data']['data']['connector'][''])
                    
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.login_url_info', response['data']['data']['connector']['url'])
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.eva_job_portal_token', response['data']['token'])
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_api_first', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_api_eva_job_portal', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_eva_job_portal_fail', False)
                else:
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_api_first', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_api_first', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_api_eva_job_portal', False)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.validate_eva_job_portal_fail', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.login_url_info', '')
                    self.env["ir.config_parameter"].sudo().set_param('equip3_eva_jobportal_integration.eva_job_portal_token', '')
                    
            except:
                raise ValidationError(f"{login.content}")
            
    
   