import random
import string
from odoo import api, fields, models, _
import pytz, logging, requests, json
from odoo.exceptions import UserError, ValidationError
import requests
from datetime import datetime, timedelta
import json
import hashlib
import hmac
import base64
import time
from requests_oauthlib import OAuth2Session
from pytz import timezone


headers = {'content-type': 'application/json', 'accept': '*/*','Accept-Encoding':'gzip, deflate, br'}
class RestPartner(models.Model):
    _inherit = 'res.partner'
    
    privy_user_name = fields.Char()
    privy_history_ids = fields.One2many('privy.register.history','partner_id')
    payload_temp = fields.Char()
    
    def generate_oauth_signature(self,method, payload, timestamp):
        api_key = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_api_key')
        secret_key = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_secret_key')
        self.payload_temp = payload
        body = payload
        if 'document' in body:
            del body['document']
        
        json_body = json.dumps(body, separators=(',', ':'))
        body_md5 = hashlib.md5(json_body.encode()).digest()
        body_md5_base64 = base64.b64encode(body_md5).decode()
        hmac_signature = f"{timestamp}:{api_key}:{method}:{body_md5_base64}"
        hmac_hash = hmac.new(secret_key.encode(), hmac_signature.encode(), hashlib.sha256)
        hmac_base64 = base64.b64encode(hmac_hash.digest()).decode()
        auth_string = f"{api_key}:{hmac_base64}"
        signature = base64.b64encode(auth_string.encode()).decode()
        payload = eval(self.payload_temp)
        return signature
    
    def check_status_contract(self,reference_number,channel_id,document_token,info):
        self.ensure_one()
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        payload = {"reference_number":reference_number,
                   "channel_id":channel_id,
                   "document_token":document_token,
                   "info":info
                   }
        
        signature = self.generate_oauth_signature("POST",payload,timestamp)
        headers['Authorization'] = f"Bearer {token}"
        headers['timestamp'] = timestamp
        headers['signature'] = signature
        
        try:
            request_api = requests.post(privy_url + '/web/api/v2/doc-signing/status',json=payload,headers=headers)      
            response = request_api.json()
            
            if request_api.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            
            return response
            

        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
        
        
    
    def send_email_privy(self,custom_signature_placement,doc_process,document_name,drag_n_drop,notify_user,document_file,posX,posY,signPage):
        self.ensure_one()
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        privy_channel_id = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        privy_enterprise_token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_enterprise_token')
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        recipients =  {
                        "user_type": "0",
                        "autosign": "0",
                        "id_user": self.privy_user_name,
                        "signer_type": "Signer",
                        "enterpriseToken":privy_enterprise_token,
                        "notify_user": "1" if notify_user else "0",
                        "drag_n_drop":drag_n_drop,
                        "posX":posX,
                        "posY":posY,
                        "signPage":signPage,
                        "detail":"1"
                    }
        
        if drag_n_drop:
            del recipients['posX']
            del recipients['posY']
            del recipients['signPage']
            
        
        payload = {
            "reference_number":f"document{self.env.company.name}{self.id}",
            "channel_id":privy_channel_id,
            "custom_signature_placement":custom_signature_placement,
            "doc_process":"0" if not doc_process else "1",
            "visibility":True,
            "doc_owner":{
                    "privyId": self.env.company.privy_id,
                    "enterpriseToken": privy_enterprise_token
                
            },
            "document":{
                "document_file":  "data:" + "application/pdf" + ";base64," + (document_file).decode('utf-8'),
                "document_name":document_name,
                "sign_process":"1"
                
            },
            "recipients": [
                    recipients
                    ]
            }
        signature = self.generate_oauth_signature("POST",payload,timestamp)
        payload = eval(self.payload_temp)
        headers['Authorization'] = f"Bearer {token}"
        headers['timestamp'] = timestamp
        headers['signature'] = signature
        
        try:
            sign = requests.post(privy_url + '/web/api/v2/doc-signing',json=payload,headers=headers)      
            response = sign.json()
            
            if sign.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            
            return response
            

        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
            
            
    def doc_signing(self,payload):
        self.ensure_one()
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        signature = self.generate_oauth_signature("POST",payload,timestamp)
        payload = eval(self.payload_temp)
        headers['Authorization'] = f"Bearer {token}"
        headers['timestamp'] = timestamp
        headers['signature'] = signature
        payload = eval(self.payload_temp)
        
        try:
            sign = requests.post(privy_url + '/web/api/v2/doc-signing',json=payload,headers=headers)      
            response = sign.json()
            
            if sign.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            
            return response
            

        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
    def generate_random_string(self,length):
        letters = string.ascii_letters  # This includes both lowercase and uppercase letters
        random_string = ''.join(random.choice(letters) for i in range(length))
        return random_string
    
    
    def register_privy(self):
        self.ensure_one()
        privy_channel_id = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        phone = self.mobile
        cleaned_phone_number = phone.replace(" ", "").replace("-", "")
        ref = f"{self.env.company.name}{self.id}{self.generate_random_string(7)}"
        payload = {"reference_number": ref.replace(" ", ""),
                   "channel_id": privy_channel_id,
                   "email": f"{self.email}",
                   "phone": f"{cleaned_phone_number}"
                   
                   }  
        method = "POST"
        signature = self.generate_oauth_signature("POST",payload,timestamp)
        payload = eval(self.payload_temp)
        headers['Authorization'] = f"Bearer {token}"
        headers['timestamp'] = timestamp
        headers['signature'] = signature
        
        try:
            register = requests.post(privy_url + '/web/api/v2/register',json=payload,headers=headers)      
            response = register.json()
            if register.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")

            exist = self.privy_history_ids.filtered(lambda line:line.email == self.email)
            if not exist:
                status = response['data']['status']
                if response['data']['status'] == 'pending':
                    status = 'Pending'
                if response['data']['status'] == 'waiting_verification':
                    status = 'Waiting Verification by Privy'
                if response['data']['status'] == 'registered':
                    status = 'Registered'
                self.privy_history_ids = [(0,0,{'name':self.name,'email':self.email,
                                                'mobile':cleaned_phone_number,
                                                'status':status,
                                                'register_token':response['data']['register_token'],
                                                'channel_id':response['data']['channel_id'],
                                                'reference_number':response['data']['reference_number'],
                                                })]
            
            if not 'registration_url' in response['data']:
                if response['data']['status'] in ('waiting_verification','registered'):
                    raise ValidationError(f"Account {self.name} already registered!") 
                
            return {
                'type': 'ir.actions.act_url',
                'url': f"{response['data']['registration_url']}",
                'target': 'new',
       
            }
        
        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )


class privyRegisterHistory(models.Model):
    _name = 'privy.register.history'
    
    partner_id = fields.Many2one('res.partner')
    name = fields.Char()
    email = fields.Char()
    mobile = fields.Char()
    registered_date = fields.Date(default=datetime.now())
    status = fields.Char()
    register_token = fields.Char()
    reference_number = fields.Char()
    channel_id = fields.Char()
    
    
    def check_status(self):
        token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        privy_url = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        payload = {"reference_number": self.reference_number,
                   "channel_id": self.channel_id,
                   "register_token": self.register_token,
                   
                   }  
        method = "POST"
        signature = self.partner_id.generate_oauth_signature(method,payload,timestamp)
        payload = eval(self.partner_id.payload_temp)
        headers['Authorization'] = f"Bearer {token}"
        headers['timestamp'] = timestamp
        headers['signature'] = signature
        try:
            check_status = requests.post(privy_url + '/web/api/v2/register/status',json=payload,headers=headers)            
            response = check_status.json()
            if check_status.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            status = response['data']['status']
            if response['data']['status'] == 'pending':
                status = 'Pending'
            if response['data']['status'] == 'waiting_verification':
                status = 'Waiting Verification by Privy'
            if response['data']['status'] == 'registered':
                status = 'Registered'
            self.status = status
            self.env.cr.commit()
            if response['data']['status'] == 'registered':
                self.partner_id.privy_user_name = response['data']['privy_id']
                
            if self.status == 'rejected' and response['data']['resend']:
                raise ValidationError(f"Please check your email from Privy to do the resend register process! \nblock_reason message :{response['data']['reject_reason']}")
            if self.status == 'rejected' and not response['data']['resend']:
                raise ValidationError(f"Please do the registration process again! \nblock_ reason message : {response['data']['reject_reason']}")
        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
