# -*- coding: utf-8 -*-

import logging
import json
import requests
from odoo import api, fields, models, _ , tools
from odoo.exceptions import Warning
from odoo.exceptions import UserError
import base64
import time
import re
import uuid



class ScanWAQRCode(models.TransientModel):
    _name = 'whatsapp.scan.qr'
    _description = 'Scan WhatsApp QR Code'

    def _get_default_image(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        Param_set = self.env['ir.config_parameter'].sudo()
        url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/status?token=' + Param.get('whatsapp_token')
        response = requests.get(url)
        json_response = json.loads(response.text)
        img = ''
        # auth_value = False
        if (response.status_code == 201 or response.status_code == 200) and (json_response['accountStatus'] == 'got qr code'):
            # qr_code_image
            # qr_image = base64.b64encode(json_response['qrCode'])
            qr_code_url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/qr_code?token=' + Param.get('whatsapp_token')
            response_qr_code = requests.get(qr_code_url)
            # json_data = response_qr_code.json()
            img = base64.b64encode(response_qr_code.content)
            # auth_value = True
            Param_set.set_param("pragmatic_odoo_delivery_boy.whatsapp_authenticate", True)
            return img

        # elif (response.status_code == 201 or response.status_code == 200) and (json_response['accountStatus'] == 'authenticated'):
        #     # Param_set.set_param("pragmatic_odoo_delivery_boy.whatsapp_authenticate", True)
        #     # return False
        #     auth_value = True
        #
        # else:
        #     # Param_set.set_param("pragmatic_odoo_delivery_boy.whatsapp_authenticate", False)
        #     # return False
        #     auth_value = True
        # Param_set.set_param("pragmatic_odoo_delivery_boy.whatsapp_authenticate", auth_value)


    qr_code_img_data= fields.Binary(default=_get_default_image)
