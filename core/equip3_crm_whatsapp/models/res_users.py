# -*- coding: utf-8 -*-
import json
import requests
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'
    _description = 'Res User for Qiscus'

    qc_email = fields.Char('Qiscus Email')
    qc_password = fields.Char('Qiscus Password')
    qc_token = fields.Char('Qiscus Token')
    qc_avatar_url = fields.Char('Qiscus Avatar')
