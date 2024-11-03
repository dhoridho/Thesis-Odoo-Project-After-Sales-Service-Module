# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
from odoo import models, fields
from odoo.exceptions import ValidationError

class IZIDashboardFilterValue(models.Model):
    _inherit = 'izi.dashboard.filter.value'
    _description = 'Hashmicro Dashboard Filter Value'



class IZIDashboardTheme(models.Model):
    _inherit = 'izi.dashboard.theme'
    _description = 'Hashmicro Dashboard Theme'




class IZIDashboardBlock(models.Model):
    _inherit = 'izi.dashboard.block'
    _description = 'Hashmicro Dashboard Block'


class IZIDashboardFilter(models.Model):
    _inherit = 'izi.dashboard.filter'
    _description = 'Hashmicro Dashboard Filter'


class IZIDashboard(models.Model):
    _inherit = 'izi.dashboard'
    _description = 'Hashmicro Dashboard'

    izi_lab_api_key = fields.Char('AI API Key', compute='_compute_izi_lab_api_key')
    izi_lab_url = fields.Char('AI URL', compute='_compute_izi_lab_api_key')
    izi_dashboard_access_token = fields.Char('AI Dashboard Access Token', compute='_compute_izi_lab_api_key')

    def _compute_izi_lab_api_key(self):
        for rec in self:
            rec.izi_lab_api_key = self.env.user.company_id.izi_lab_api_key
            rec.izi_lab_url = self.env['ir.config_parameter'].sudo().get_param('izi_lab_url')
            rec.base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rec.izi_dashboard_access_token = self.env['ir.config_parameter'].sudo().get_param('izi_dashboard.access_token')