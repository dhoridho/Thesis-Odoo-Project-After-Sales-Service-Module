import random
import string
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from .privy_integration import privyIntegration


class privyAccountRegistration(models.Model):
    _name = 'privy.account.registration'
    _order = 'id desc'
    
    name = fields.Char()
    email = fields.Char()
    mobile = fields.Char()
    registered_date = fields.Date(default=datetime.now())
    status = fields.Char(default='Draft',copy=False)
    privy_id = fields.Char(copy=False)
    register_token = fields.Char(copy=False)
    reference_number = fields.Char(copy=False)
    channel_id = fields.Char(copy=False)
    channel_id = fields.Char(copy=False)
    register_token = fields.Char(copy=False)
    partner_id = fields.Many2one('res.partner')
    
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for data in self:
            if data.partner_id:
                data.name = data.partner_id.name
                data.email = data.partner_id.email
                data.mobile = data.partner_id.mobile
    
    
    
    def generate_random_string(self,length):
        letters = string.ascii_letters  # This includes both lowercase and uppercase letters
        random_string = ''.join(random.choice(letters) for i in range(length))
        return random_string
    
    
    def check_status(self):
        payload = {"reference_number": self.reference_number,
                   "channel_id": self.channel_id,
                   "register_token": self.register_token,
                   }
        response = privyIntegration().check_status(payload)
        status = response['data']['status']
        if response['data']['status'] == 'pending':
            status = 'Pending'
        if response['data']['status'] == 'waiting_verification':
            status = 'Waiting Verification by Privy'
        if response['data']['status'] == 'waiting_otp':
            status = 'Waiting OTP'
        if response['data']['status'] == 'registered':
            status = 'Registered'
        self.status = status
        self.env.cr.commit()
        if response['data']['status'] == 'registered':
            self.privy_id = response['data']['privy_id']
        
          
        
    
    def confirm(self):
        self.ensure_one()
        phone = self.mobile
        privy_channel_id = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        cleaned_phone_number = phone.replace(" ", "").replace("-", "")
        ref = f"{self.env.company.name}{self.id}{self.generate_random_string(7)}"
        payload = {"reference_number": ref.replace(" ", ""),
                   "channel_id": privy_channel_id,
                   "email": f"{self.email}",
                   "phone": f"{cleaned_phone_number}"
                   
                   }  
        response = privyIntegration().register_privy(payload)
        status = response['data']['status']
        if response['data']['status'] == 'pending':
            status = 'Pending'
        if response['data']['status'] == 'waiting_verification':
            status = 'Waiting Verification by Privy'
        if response['data']['status'] == 'waiting_otp':
            status = 'Waiting OTP'
        if response['data']['status'] == 'registered':
            status = 'Registered'
        self.status = status
        self.reference_number = response['data']['reference_number']
        self.channel_id = response['data']['channel_id']
        self.register_token = response['data']['register_token']
        # if 'registration_url' in response['data']:
        #     return {
        #         'type': 'ir.actions.act_url',
        #         'url': f"{response['data']['registration_url']}",
        #         'target': 'new',
       
        #     }
            