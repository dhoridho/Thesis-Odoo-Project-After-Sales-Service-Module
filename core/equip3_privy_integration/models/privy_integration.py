import base64
import hashlib
import hmac
import json
import requests
from odoo.http import request
from odoo.exceptions import ValidationError
from datetime import datetime
headers = {'content-type': 'application/json'}

class privyIntegration(object):
    def __init__(self,):
        self.privy_channel_id = request.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        self.privy_url = request.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_base_url')
        self.token = request.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_access_token')
        self.timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        self.api_key = request.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_api_key')
        self.secret_key = request.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_secret_key')
        self.payload_temp =  None
        
        
    def generate_oauth_signature(self,method, payload, timestamp):
        self.payload_temp = payload.copy()
        body = payload
        if 'document' in body:
            del body['document']
        json_body = json.dumps(body, separators=(',', ':'))
        body_md5 = hashlib.md5(json_body.encode()).digest()
        body_md5_base64 = base64.b64encode(body_md5).decode()
        hmac_signature = f"{timestamp}:{self.api_key}:{method}:{body_md5_base64}"
        hmac_hash = hmac.new(self.secret_key.encode(), hmac_signature.encode(), hashlib.sha256)
        hmac_base64 = base64.b64encode(hmac_hash.digest()).decode()
        auth_string = f"{self.api_key}:{hmac_base64}"
        signature = base64.b64encode(auth_string.encode()).decode()
        return signature

    def register_privy(self,payload):
        signature = self.generate_oauth_signature("POST",payload,self.timestamp)
        payload = self.payload_temp
        headers['Authorization'] = f"Bearer {self.token}"
        headers['timestamp'] = self.timestamp
        headers['signature'] = signature
        
        try:
            register = requests.post(self.privy_url + '/web/api/v2/register',json=payload,headers=headers)      
            response = register.json()
            if register.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")

            return response
        
        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
    def check_status(self,payload):
        method = "POST"
        signature = self.generate_oauth_signature(method,payload,self.timestamp)
        payload = self.payload_temp
        headers['Authorization'] = f"Bearer {self.token}"
        headers['timestamp'] = self.timestamp
        headers['signature'] = signature
        try:
            check_status = requests.post(self.privy_url + '/web/api/v2/register/status',json=payload,headers=headers)            
            response = check_status.json()
            if check_status.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            return response
        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connectio")
    
    
    def doc_signing(self,payload):
        signature = self.generate_oauth_signature("POST",payload,self.timestamp)
        headers['Authorization'] = f"Bearer {self.token}"
        headers['timestamp'] = self.timestamp
        headers['signature'] = signature
        payload = self.payload_temp
        
        try:
            sign = requests.post(self.privy_url + '/web/api/v2/doc-signing',json=payload,headers=headers)      
            response = sign.json()
            
            if sign.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            
            return response
            

        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )

    def doc_status(self,payload):        
        signature = self.generate_oauth_signature("POST",payload,self.timestamp)
        headers['Authorization'] = f"Bearer {self.token}"
        headers['timestamp'] = self.timestamp
        headers['signature'] = signature
        payload = self.payload_temp
        try:
            request_api = requests.post(self.privy_url + '/web/api/v2/doc-signing/status',json=payload,headers=headers)      
            response = request_api.json()
            if request_api.status_code != 201:
                raise ValidationError(f"{response['error']['errors']}")
            return response
        except requests.exceptions.ConnectionError:
            raise ValidationError("Server connection failed! \n"
                                      "check connection or IP whitelist privy"
                                      )
  
  