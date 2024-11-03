import base64
from datetime import datetime
import hashlib
import json
import sys
import requests
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError
    
class AccountingSettingMy(models.Model):
    _name = 'accounting.setting.my'
    
    name = fields.Char()
    lhdn_url = fields.Char(string="URL")
    valid_lhdn = fields.Boolean(default=False)
    invalid_lhdn = fields.Boolean(default=False)
    lhdn_client_id = fields.Char(string="Client ID")
    lhdn_client_secret = fields.Char(string="Client Secret")
    status = fields.Selection([('valid','Authentication is Valid !'),('invalid','Authentication is Invalid!')])
    taxpayer_tin = fields.Char()
    taxpayer_type = fields.Selection([('NRIC','NRIC'),('PASSPORT','PASSPORT'),('BRN','BRN'),('ARMY','ARMY')],default='BRN')
    taxpayer_number = fields.Char()
    tin_status = fields.Selection([('valid','Authentication is Valid !'),('invalid','Authentication is Invalid!')])
    access_token = fields.Char()
    
    
    def action_validate_login(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
                }
        data = {
            'client_id': self.lhdn_client_id,
            'client_secret': self.lhdn_client_secret,
            'grant_type':'client_credentials',
            'scope':'InvoicingAPI'
            }
        try:
            response = requests.post(self.lhdn_url+'/connect/token', headers=headers, data=data)
            if response.status_code == 200:
                self.status = 'valid'
                response_json = response.json()
                self.access_token =  response_json['access_token']
            else:
                self.status = 'invalid'
                
        except Exception as e:
            tb = sys.exc_info()
            raise UserError(e.with_traceback(tb[2]))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
            }
        
        
    def action_validate_tin(self):
        if not self.access_token:
            raise ValidationError("Token is Empty! Please Login First")
        header = {"Authorization": "Bearer " + self.access_token}
        params = {
            'idType': self.taxpayer_type,
            'idValue': self.taxpayer_number
            }
        try:
            response = requests.get(self.lhdn_url+f'/api/v1.0/taxpayer/validate/{self.taxpayer_tin}', params=params,headers=header)
            if response.status_code == 200:
                self.tin_status = 'valid'
            else:
                self.tin_status = 'invalid'
                
        except Exception as e:
            tb = sys.exc_info()
            raise UserError(e.with_traceback(tb[2]))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
            }