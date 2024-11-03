from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests

class ResCompany(models.Model):
    _inherit = 'res.company'

    pjap_x_token = fields.Char('PJAP X-Token')
    npwp = fields.Char('NPWP')
    is_centralized_efaktur = fields.Boolean('Centralized E-Faktur')
    is_use_nik_for_ebupot = fields.Boolean('Use NIK for Ebupot', default=False)
    tax_cutter_nik = fields.Char('Tax Cutter NIK')

    @api.constrains('vat')
    def _constrains_vat(self):
        for rec in self:
            if rec.vat:
                if self.search_count([('vat', '=', rec.vat)]) > 1:
                    raise ValidationError(_('The NPWP Number cannot be the same with another company'))

    def pajak_express_url(self):
        pajak_express_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_url')
        return pajak_express_url

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
    
    def generate_pjap_x_token(self):
        self.ensure_one()
        pajak_express_url = self.pajak_express_url()
        login  = self.login()
        if not self.vat:
            raise ValidationError(_('VAT must be filled.'))
        if login.status_code == 200:
            response = login.json()
            npwp = str(self.vat).replace('.','')
            npwp = str(npwp).replace('-','')
            token = response['data']['token']
            x_token = self.generate_api_secret(pajak_express_url,npwp,token)
            self.pjap_x_token = x_token
