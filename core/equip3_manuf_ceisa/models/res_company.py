# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from cryptography.fernet import Fernet
import sys
import json
import requests
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Res Company'


    @api.model
    def default_get(self, fields):
        res = super(ResCompany, self).default_get(fields)
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            res['is_ceisa_it_inventory'] = ceisa_inventory
        return res

    ceisa_user = fields.Char('CEISA User')
    ceisa_password = fields.Char('CEISA Password')
    ceisa_user_token = fields.Char('CEISA User Token')
    ceisa_user_key = fields.Char('CEISA User Key')
    # ceisa_token = fields.Char('CEISA Token')
    # ceisa_refresh_token = fields.Char('Refresh Token')
    # ceisa_id_token = fields.Char('ID Token')
    # ceisa_token_type = fields.Char('Token Type')
    # ceisa_status = fields.Char('Status')
