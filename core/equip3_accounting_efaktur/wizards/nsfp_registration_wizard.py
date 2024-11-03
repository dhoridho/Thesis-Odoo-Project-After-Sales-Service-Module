from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import requests

class NSFPRegistrationWizard(models.TransientModel):
    _name = 'nsfp.registration.wizard'
    _description = 'NSFP Registration Wizard'
    
    fiscal_year = fields.Many2one('sh.fiscal.year')
    start = fields.Char(string='Start', size=100, help="E-Faktur Format xxx-xx-xxxxxxxx" ,default="0000000000000")
    end = fields.Char(string='End', size=100,default="0000000000000")
    
    def pajak_express_url(self):
        pajak_express_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_url')
        return pajak_express_url
    
    def pajak_express_transaction_url(self):
        pajak_express_transaction_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_transaction_url')
        return pajak_express_transaction_url
        
    def generate_api_secret(self,url,npwp,token):
        header = {"Authorization": f"Bearer {token}",
                   "npwp":npwp
                   }
        api_secret = requests.get(url + '/api/client-store',headers=header)
        secret_response =  api_secret.json()
        header_x = {"Authorization": f"Bearer {token}",
                    "X-Tenant":"foo",
                    "api-key":secret_response['data']['api_key'],
                    "api-secret":secret_response['data']['api_secret']
                   }
        x_token = requests.post(url+"/api/client-token",headers=header_x)
        x_token_response = x_token.json()
        return x_token_response['data']['token']
   
    def login(self):
       pajak_express_url = self.pajak_express_url()
       pajak_express_username = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_username')
       pajak_express_password = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_password')
       payload = {'email':pajak_express_username,'password':pajak_express_password}
       login = requests.post(pajak_express_url + '/api/login',data=payload)
       return login
    
    def generate_api_secret(self,url,npwp,token):
        header = {"Authorization": f"Bearer {token}",
                   "npwp":npwp
                   }
        api_secret = requests.get(url + '/api/client-store',headers=header)
        secret_response =  api_secret.json()
        header_x = {"Authorization": f"Bearer {token}",
                    "X-Tenant":"foo",
                    "api-key":secret_response['data']['api_key'],
                    "api-secret":secret_response['data']['api_secret']
                   }
        x_token = requests.post(url+"/api/client-token",headers=header_x)
        x_token_response = x_token.json()
        return x_token_response['data']['token']
    
    @api.onchange('fiscal_year')
    def _onchange_fiscal_year(self):
        for record in self:
            input_format = '%Y'
            output_format = '%y'
            if record.fiscal_year:
                year = datetime.strptime(record.fiscal_year.name,input_format)
                start = str(record.start)
                start = start[:3] + year.strftime(output_format) + start[5:]
                record.start = start
                
                end = str(record.end)
                end = end[:3] + year.strftime(output_format) + end[5:]
                record.end = end

                
    def save(self):
        pajak_express_url = self.pajak_express_url()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            npwp = response['data']['npwp_log']
            token = response['data']['token']
            x_token = self.generate_api_secret(pajak_express_url,npwp,token)
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            json_request = {"id": False,
                            "nfAwal": "0002300250041",
                            "nfAkhir": "0002300250045",
                            "tanggal": "20230101",
                            "terakhir": ""
                            }
            
            pajak_keluaran = requests.post(pajak_express_transaction_url + "/efaktur/nsfp",headers=header_x,json=json_request)
            pajak_response =  pajak_keluaran.json()
            
            
        


