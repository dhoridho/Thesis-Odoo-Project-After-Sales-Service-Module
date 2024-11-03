# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
from odoo.modules import get_resource_path


class AwesomeThemeSettingBase(models.Model):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.theme_setting_base'
    _description = 'user setting base'

    first_visited = fields.Boolean(string="inited", default=False)

    layout_mode = fields.Selection(
        string="layout mode",
        selection=[('layout_mode1', 'layout_mode1'),
                   ('layout_mode2', 'layout_mode2'),
                   ('layout_mode3', 'layout_mode3')],
        default="layout_mode1")

    login_style = fields.Selection(
        string="login style",
        selection=[('login_style1', 'login_style1'),
                   ('login_style2', 'login_style2'),
                   ('login_style3', 'login_style3'),
                   ('login_style4', 'login_style4')],
        default='login_style1')

    control_panel_mode = fields.Selection(
        string="Control Panel Mode",
        selection=[('mode1', 'mode1'),
                   ('mode2', 'mode2'),
                   ('mode3', 'mode3')],
        default="mode1")

    app_tab_selected_style = fields.Selection(
        selection=[('style1', 'style1'),
                   ('style2', 'style2')],
        default='style1')

    current_theme_mode = fields.Many2one(
        comodel_name='awesome_theme_pro.theme_mode',
        string="Current Theme Mode")

    current_theme_style = fields.Many2one(
        string="Current Theme Style",
        comodel_name="awesome_theme_pro.theme_style",
        domain="[('theme_mode', '=', current_theme_mode)]",
        help="just use when theme style mode is system")

    form_style = fields.Selection(
        string="Form Style",
        selection=[('normal', 'normal'),
                   ('awesome_popup', 'awesome_popup')],
        default='normal')

    dialog_pop_style = fields.Selection(
        string="dialog pop up style",
        selection=[('normal', 'awesome-normal'),
                   ('awesome-effect-scale', 'awesome-scale'),
                   ('awesome-effect-slide-in-right', 'awesome-slide-in-right'),
                   ('awesome-effect-slide-in-bottom', 'awesome-slide-in-bottom'),
                   ('awesome-effect-fall', 'awesome-fall'),
                   ('awesome-effect-flip-horizontal', 'awesome-flip-horizontal'),
                   ('awesome-effect-effect-flip-vertical', 'awesome-effect-flip-vertical'),
                   ('awesome-effect-super-scaled', 'awesome-super-awesome-scaled'),
                   ('awesome-effect-sign-in', 'awesome-sign-in'),
                   ('awesome-effect-effect-newspaper', 'awesome-effect-newspaper'),
                   ('awesome-effect-rotate-bottom', 'awesome-rotate-bottom'),
                   ('awesome-effect-rotate-left', 'awesome-rotate-left')],
        default='normal')

    button_style = fields.Selection(
        string="Button Style",
        selection=[("btn-style-normal", "btn-style-normal"),
                   ("btn-style-slant", "btn-style-slant")],
        default="btn-style-normal")

    table_style = fields.Selection(
        string="table style",
        selection=[('normal', 'normal'),
                   ('bordered', 'bordered')],
        default="normal")

    font_name = fields.Selection(
        string="Font Name",
        selection=[('Roboto', 'Roboto'),
                   ('sans-serif', 'sans-serif'),
                   ('Helvetica', 'Helvetica'),
                   ('Arial', 'Arial'),
                   ('Verdana', 'Verdana'),
                   ('Tahoma', 'Tahoma'),
                   ('Trebuchet MS', 'Trebuchet MS')],
        default="Roboto")

    multi_tab_mode = fields.Boolean(string="multi tab mode", default=True)
    show_app_name = fields.Boolean(string="Show App Name", default=True)
    rtl_mode = fields.Boolean(string="RTL MODE", default=False)
    favorite_mode = fields.Boolean(string="Favorite Mode", default=False)
    allow_debug = fields.Boolean(string="Allow Debug", default=True)

    # pwa
    pwa_name = fields.Char(string="Pwa Name", default="Awesome Odoo")
    pwa_short_name = fields.Char(string="Pwa Short Name", default="Awesome")
    pwa_background_color = fields.Char(string="Pwa Background Color", default="#2E69B5")
    pwa_theme_color = fields.Char(string="Pwa Theme Color", default="#2E69B5")

    system = fields.Boolean(string="system", default=False)

    def _get_default_small_128(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path(
                'awesome_theme_pro', 'static', 'images', 'icons', "icon-128x128.png"), 'rb').read())

    # icon128x128
    icon128x128 = fields.Binary(
        string="icon128x128",
        default=_get_default_small_128)
    icon128_url = fields.Char(string="icon128 url", compute="_compute_icon128_url")

    @api.depends('icon128x128')
    def _compute_icon128_url(self):
        '''
        icon 128 url
        :return:
        '''
        for record in self:
            if record.icon128x128:
                record.icon128_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon128x128'.format(var_id=record.id)

    def _get_default_small_144(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path(
                'awesome_theme_pro', 'static', 'images', 'icons', "icon-144x144.png"), 'rb').read())

    icon144x144 = fields.Binary(
        string="icon144x144", default=_get_default_small_144)
    icon144_url = fields.Char(string="icon144 url", compute="_compute_icon144_url")

    @api.depends('icon144x144')
    def _compute_icon144_url(self):
        '''
        icon 128 url
        :return:
        '''
        for record in self:
            if record.icon144x144:
                record.icon144_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon144x144'.format(var_id=record.id)

    def _get_default_small_152(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path(
                'awesome_theme_pro', 'static', 'images', 'icons', "icon-152x152.png"), 'rb').read())

    icon152x152 = fields.Binary(
        string="icon152x152", default=_get_default_small_152)
    icon152_url = fields.Char(string="icon152 url", compute="_compute_icon152_url")

    @api.depends('icon152x152')
    def _compute_icon152_url(self):
        '''
        icon 128 url
        :return:
        '''
        for record in self:
            if record.icon152x152:
                record.icon152_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon152x152'.format(var_id=record.id)

    def _get_default_small_192(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path(
                'awesome_theme_pro', 'static', 'images', 'icons', "icon-192x192.png"), 'rb').read())

    icon192x192 = fields.Binary(
        string="icon192x192", default=_get_default_small_192)
    icon192_url = fields.Char(string="icon192 url", compute="_compute_icon192_url")

    @api.depends('icon192x192')
    def _compute_icon192_url(self):
        '''
        icon 128 url
        :return:
        '''
        for record in self:
            if record.icon192x192:
                record.icon192_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon192x192'.format(var_id=record.id)

    def _get_default_small_256(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path('awesome_theme_pro', 'static', 'images', 'icons', "icon-256x256.png"), 'rb').read())

    icon256x256 = fields.Binary(
        string="icon256x256", default=_get_default_small_256)
    icon256_url = fields.Char(string="icon256 url", compute="_compute_icon256_url")

    @api.depends('icon256x256')
    def _compute_icon256_url(self):
        '''
        icon 256 url
        :return:
        '''
        for record in self:
            if record.icon256x256:
                record.icon256_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon256x256'.format(var_id=record.id)

    def _get_default_small_512(self):
        '''
        get the default small logo
        :return:
        '''
        return base64.b64encode(
            open(get_resource_path(
                'awesome_theme_pro', 'static', 'images', 'icons', "icon-512x512.png"), 'rb') .read())

    icon512x512 = fields.Binary(
        string="icon512x512", default=_get_default_small_512)
    icon512_url = fields.Char(string="icon512 url", compute="_compute_icon512_url")

    @api.depends('icon512x512')
    def _compute_icon512_url(self):
        '''
        icon 128 url
        :return:
        '''
        for record in self:
            if record.icon512x512:
                record.icon512_url = \
                    '/web/image/awesome_theme_pro.theme_setting_base/{var_id}/icon512x512'.format(
                        var_id=record.id)

