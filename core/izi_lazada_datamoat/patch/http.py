# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo.http import WebRequest


def lazop_app_key(self):
    appkey = self.env['ir.config_parameter'].sudo().get_param('lazop.app_key')
    return appkey


WebRequest.lazop_app_key = lazop_app_key
