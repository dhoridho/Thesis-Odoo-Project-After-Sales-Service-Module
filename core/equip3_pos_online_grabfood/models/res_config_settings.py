# -*- coding: utf-8 -*-

import os 
import base64
import json
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad

from odoo import fields, models, api
from datetime import datetime

password = "WaHkJtdR" #only for the server
separator = '.h546eda4d1' #only for the server

def base64Encoding(input):
    dataBase64 = base64.b64encode(input)
    dataBase64P = dataBase64.decode("ascii")
    return dataBase64P

def base64Decoding(input):
    return base64.decodebytes(input.encode("ascii"))

def aesCbcPbkdf2Encrypt(password, separator, plaintext):
    passwordBytes = password.encode("ascii")
    salt = bytes(password, 'utf-8')
    PBKDF2_ITERATIONS = 15000
    encryptionKey = PBKDF2(passwordBytes, salt, 32, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)
    cipher = AES.new(encryptionKey, AES.MODE_CBC)
    ciphertext = cipher.encrypt(pad(plaintext.encode("ascii"), AES.block_size)) 
    base64_ciphertext = base64Encoding(ciphertext)[:-1] # remove padding =
    base64_iv = base64Encoding(cipher.iv)[:-1] # remove padding =
    return base64_ciphertext + separator + base64_iv

def aesCbcPbkdf2Decrypt(password, separator, data): 
    data = data.split(separator)
    ciphertext = base64Decoding(data[0] + '=' ) # Add padding =
    iv = base64Decoding(data[1] + '=' ) # Add padding =
    passwordBytes = password.encode("ascii")
    salt = bytes(password, 'utf-8')
    PBKDF2_ITERATIONS = 15000
    decryptionKey = PBKDF2(passwordBytes, salt, 32, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)
    cipher = AES.new(decryptionKey, AES.MODE_CBC, iv)
    decryptedtext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decryptedtext.decode("utf-8") 

def random_str(n):
    base = 'abcefghijklmnopqrstuvwxzyABCEFGHIJKLMNOPQRSTUVWXZY0123456789'

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    grabfood_environment = fields.Selection([('sandbox','Sandbox (Testing)'), ('production','Production')], string='Environment', default='sandbox', config_parameter='base_setup.grabfood_environment')

    #Sandbox Configuration
    grabfood_sandbox_client_id = fields.Char('Client ID', config_parameter='base_setup.grabfood_sandbox_client_id')
    grabfood_sandbox_client_secret = fields.Char('Client Secret', config_parameter='base_setup.grabfood_sandbox_client_secret')

    #Production Configuration
    grabfood_production_client_id = fields.Char('Client ID', config_parameter='base_setup.grabfood_production_client_id')
    grabfood_production_client_secret = fields.Char('Client Secret', config_parameter='base_setup.grabfood_production_client_secret')
    
    oloutlet_client_id = fields.Char('Partner client ID', config_parameter='base_setup.oloutlet_client_id', default='api.grab@mail.com')
    oloutlet_client_secret = fields.Char('Partner client secret', config_parameter='base_setup.oloutlet_client_secret', default='W8EAxWd3')


    def _olo_generate_access_token(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        internal_client_id = ConfigParameter.get_param('base_setup.oloutlet_client_id')
        internal_client_secret = ConfigParameter.get_param('base_setup.oloutlet_client_secret')
        data = json.dumps({
            'id': internal_client_id,
            'grant_type': 'client_credentials',
            'scope': 'hashmicro',
            'expired': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        ciphertextBase64 = aesCbcPbkdf2Encrypt(password, separator, data)
        return ciphertextBase64

    def _olo_check_access_token(self, access_token):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        is_pass = False
        data = {}
        token = access_token and access_token[7:] or False

        if token:
            try:
                decryptedtext = aesCbcPbkdf2Decrypt(password, separator, token)
                data = json.loads(decryptedtext)
                is_pass = True
            except Exception as e:
                is_pass = False

        if is_pass:
            internal_client_id = ConfigParameter.get_param('base_setup.oloutlet_client_id')
            if data.get('id') == internal_client_id:
                is_pass = True
            else:
                is_pass = False

        if is_pass:
            if data.get('scope') == 'hashmicro':
                is_pass = True
            else:
                is_pass = False

        if is_pass:
            if data.get('grant_type') == 'client_credentials':
                is_pass = True
            else:
                is_pass = False

        return is_pass

    def _olo_check_user_secret(self, client_id, client_secret):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        internal_client_id = ConfigParameter.get_param('base_setup.oloutlet_client_id')
        internal_client_secret = ConfigParameter.get_param('base_setup.oloutlet_client_secret')
        if internal_client_id and internal_client_secret and client_id and client_secret:
            if internal_client_id == client_id and internal_client_secret == client_secret:
                return True
        return False