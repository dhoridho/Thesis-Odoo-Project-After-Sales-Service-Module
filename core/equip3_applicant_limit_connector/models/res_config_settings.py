# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Equip3ApplicantLimit(models.TransientModel):
    _inherit = 'res.config.settings'

    is_limit_applicant = fields.Boolean(config_parameter='equip3_applicant_limit_connector.is_limit_applicant')
    server_domain = fields.Char(config_parameter='equip3_applicant_limit_connector.server_domain',default="https://")
    user = fields.Char(config_parameter='equip3_applicant_limit_connector.user')
    password = fields.Char(config_parameter='equip3_applicant_limit_connector.password')
    secret_key = fields.Char(config_parameter='equip3_applicant_limit_connector.secret_key')