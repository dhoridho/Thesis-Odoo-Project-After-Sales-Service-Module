# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AwesomeImportStyle(models.TransientModel):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.import_theme_style'
    _description = 'user setting'

    file = fields.Binary(string="theme file", required=True)
