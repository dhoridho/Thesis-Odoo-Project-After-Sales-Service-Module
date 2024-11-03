# -*- coding: utf-8 -*-

import base64
import requests
import os
import json
import tempfile
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from base64 import b64encode


class SaleCustomerSignature(models.Model):
    _name = "sale.customer.esignature"
    _rec_name = "full_name"
    _description = "Sale Customer Esignature"

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)
    active = fields.Boolean(string='Active', default=False)
    terms_conditions = fields.Boolean(string='Terms and Conditions', default=False)
    identity_number = fields.Char(string="Identity Number")
    full_name = fields.Char(string="Full Name")
    date_of_birth = fields.Date(string="Date Of Birth")
    phone_no = fields.Char(string="Phone No")
    email_id = fields.Char(string="Email")
    selfie_img = fields.Binary(string="Selfie Image", attachment=True)
    selfie_img_name = fields.Char(string='Selfie Image Name', default='selfie.png')
    identity_image = fields.Binary(string="Identity Id", attachment=True)
    identity_image_name = fields.Char(string="Identity Image Name", default="identity.png")
    country_id = fields.Many2one('res.country', string="Country")
    account_status = fields.Char(string='Account Status')
    reason = fields.Char(string="Reason")
    privid_message = fields.Text(string='Message')
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)

    def check_privy_status(self):
        self.ensure_one()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        privy_url = IrConfigParam.get_param('privy_url')
        privy_username = IrConfigParam.get_param('privy_username')
        privy_password = IrConfigParam.get_param('privy_password')
        privy_merchant_key = IrConfigParam.get_param('privy_merchant_key')
        if privy_url and privy_username and privy_password and privy_merchant_key:
            userpass = privy_username + ':' + privy_password
            encoded_u = base64.b64encode(userpass.encode()).decode()
            headers = {
              'Merchant-Key': privy_merchant_key,
              'Authorization': 'Basic %s' % encoded_u,
            }
            payload = {
                'token': self.user_id.partner_id.signature_token,
            }
            privy_url += 'registration/status'
            response = requests.request("POST", privy_url, headers=headers, data=payload)
            try:
                os.remove(identity_file_path)
                os.remove(selfie_file_path)
            except Exception as e:
                pass

            result = response.json()
            if result.get('code') in [200, 201]:
                status = result.get('data', False).get('status', False)
                reason = result.get('message')
                token = result.get('data', False).get('userToken', False)
                self.user_id.partner_id.write({
                    'signature_reason': reason,
                    'signature_token': token,
                    'signature_status': status.capitalize() if status else '',
                })

    def unlink(self):
        if self.user_id:
            self.user_id.partner_id.write({
                'signature_name': '',
                'date_of_birth': '',
                'signature_mobile': '',
                'signature_status': '',
                'signature_email': '',
                'selfie_img': '',
                'selfie_img_name': '',
                'identity_image': '',
                'identity_image_name': '',
                'signature_country_id': False,
                'signature_reason': '',
                'signature_token': '',
            })
        return super(SaleCustomerSignature, self).unlink()

    def send_privy_data(self):
        self.ensure_one()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        privy_url = IrConfigParam.get_param('privy_url')
        privy_username = IrConfigParam.get_param('privy_username')
        privy_password = IrConfigParam.get_param('privy_password')
        privy_merchant_key = IrConfigParam.get_param('privy_merchant_key')
        if privy_url and privy_username and privy_password and privy_merchant_key:
            email = self.email_id
            phone = self.phone_no
            identity_number = self.identity_number
            name = self.full_name.capitalize()
            birth_date = self.date_of_birth.strftime(DEFAULT_SERVER_DATE_FORMAT)
            payload = {
                'email': email,
                'phone': phone,
                'identity': '{"nik": "'+ identity_number +'","nama":"'+ name +'","tanggalLahir":"'+ birth_date +'"}'
            }
            identity_file_path = tempfile.mktemp(suffix='.png')
            selfie_file_path = tempfile.mktemp(suffix='.png')
            files = []

            if self.identity_image:
                identity_imgdata = base64.b64decode(self.identity_image)
                with open(identity_file_path, 'wb') as identity:
                    identity.write(identity_imgdata)
                files.append(('ktp', ('identity.png',open(identity_file_path,'rb'), 'image/png')))   
            if self.selfie_img:
                selfie_imgdata = base64.b64decode(self.selfie_img)
                
                with open(selfie_file_path, 'wb') as selfie:
                    selfie.write(selfie_imgdata)
                files.append(('selfie', ('selfie.png',open(selfie_file_path,'rb'), 'image/png')))

            # files = [
            #   ('ktp', ('identity.png',open(identity_file_path,'rb'), 'image/png')),
            #   ('selfie', ('selfie.png',open(selfie_file_path,'rb'), 'image/png'))
            # ]

            userpass = privy_username + ':' + privy_password
            encoded_u = base64.b64encode(userpass.encode()).decode()
            headers = {
              'Merchant-Key': privy_merchant_key,
              'Authorization': 'Basic %s' % encoded_u,
            }
            privy_url += 'registration'
            # response = requests.request("POST", privy_url, headers=headers, data=payload, files=files)
            try:
                os.remove(identity_file_path)
                os.remove(selfie_file_path)
            except Exception as e:
                pass

            # result = response.json()
            # if result.get('code') in [200, 201]:
            #     status = result.get('data', False).get('status', False)
            #     reason = result.get('message')
            #     token = result.get('data', False).get('userToken', False)
            self.user_id.partner_id.write({
                'identity_number': self.identity_number,
                'signature_name': self.full_name,
                'date_of_birth': self.date_of_birth,
                'signature_mobile': self.phone_no,
                # 'signature_status': status.capitalize() if status else '',
                'signature_email': self.email_id,
                'selfie_img': self.selfie_img,
                'selfie_img_name': self.selfie_img_name,
                'identity_image': self.identity_image,
                'identity_image_name': self.identity_image_name,
                'signature_country_id': self.country_id,
                # 'signature_reason': reason,
                # 'signature_token': token,
            })
            # qwert
            # self.privid_message = response.text
