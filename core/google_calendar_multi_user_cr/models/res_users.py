# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):

    _inherit = 'res.users'

    cal_client_id = fields.Char("Client ID", config_parameter='google_calendar_client_id', default='')
    cal_client_secret = fields.Char("Client Secret", config_parameter='google_calendar_client_secret', default='')