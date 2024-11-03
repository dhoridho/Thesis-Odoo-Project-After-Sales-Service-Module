from odoo import tools, api, fields, models, _
from datetime import date, datetime
from lxml import etree
import pytz
from pytz import timezone, UTC
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError

from lxml import etree
import logging
import requests, json
import base64

# class ResCompany(models.Model):
#     _inherit = "res.company"

#     is_call_bi_api = fields.Boolean("Get Currency from BI (Bank Indonesia)")

class ResConfigSetting(models.TransientModel):
    _inherit = "res.config.settings"

    is_call_bi_api = fields.Boolean("Get Currency from BI (Bank Indonesia)", config_parameter='base.is_call_bi_api')
    type_bi_currency = fields.Selection([
        ('average', 'Average Currency'),
        ('buy', 'Buy Currency'),
        ('sell', 'Sell Currency'),
    ], string="BI Rate Based on:", default="average", config_parameter="base.type_bi_currency")
    is_call_kemenkeu_api = fields.Boolean("Get Currency from Kemenkeu", config_parameter='base.is_call_kemenkeu_api')
    token_kemenkeu_api = fields.Char("Access Token Kemenkeu", config_parameter='base.token_kemenkeu_api')
