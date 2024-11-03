# -*- coding: utf-8 -*-

import base64
import io

from odoo import api, fields, models, tools
from odoo.modules.module import get_resource_path
from random import randrange
from PIL import Image


class AwesomeUserSetting(models.TransientModel):
    '''
    awsome user setting
    '''
    _inherit = 'res.config.settings'
    _inherits = {'awesome_theme_pro.theme_setting_base': 'setting_id'}

    theme_setting_mode = fields.Selection(
        string="theme style mode",
        selection=[('system', 'system'),
                   ('company', 'company'),
                   ('user', 'user')],
        default='system')

    pwa_mode = fields.Selection(
        string="Pwa Mode",
        selection=[('company', 'company'), ('system', 'system')], default='system')

    allow_debug = fields.Boolean(string="allow debug", default=False)
    # web_icon = fields.Binary(string='Web Favicon Icon', default='static/src/img/favicon.png')

    # just use the fields info
    setting_id = fields.Many2one(
        comodel_name="awesome_theme_pro.theme_setting_base",
        required=True,
        ondelete="cascade",
        string="setting id")

    window_default_title = fields.Char(string="login title", default="Awesome Odoo")
    powered_by = fields.Char(string="powered by", default="Awesome Odoo")

    @api.model
    def get_theme_setting(self):
        '''
        get the theme setting, it is usefull when the mode is system
        :return:
        '''
        config = self.env['ir.config_parameter'].sudo()

        layout_mode = config.get_param(
            key='awesome_theme_pro.layout_mode', default='layout_mode1')
        login_style = config.get_param(
            key='awesome_theme_pro.login_style', default='login_style1')
        theme_setting_mode = config.get_param(
            key='awesome_theme_pro.theme_setting_mode', default='system')
        current_theme_mode = config.get_param(
            key='awesome_theme_pro.current_theme_mode', default=False)
        current_theme_style = config.get_param(
            key='awesome_theme_pro.current_theme_style', default=False)
        form_style = config.get_param(
            key='awesome_theme_pro.form_style', default='normal')
        multi_tab_mode = config.get_param(
            key="awesome_theme_pro.multi_tab_mode", default=True)
        dialog_pop_style = config.get_param(
            key="awesome_theme_pro.dialog_pop_style", default='normal')
        button_style = config.get_param(
            key="awesome_theme_pro.button_style", default='btn-style-normal')
        control_panel_mode = config.get_param(
            key="awesome_theme_pro.control_panel_mode", default='mode1')

        table_style = config.get_param(key="awesome_theme_pro.table_style", default='normal')
        font_name = config.get_param(key="awesome_theme_pro.font_name", default='Roboto')
        show_app_name = config.get_param(key="awesome_theme_pro.show_app_name", default=True)
        rtl_mode = config.get_param(key="awesome_theme_pro.rtl_mode", default=False)
        favorite_mode = config.get_param(key="awesome_theme_pro.favorite_mode", default=False)
        window_default_title = config.get_param(key="awesome_theme_pro.window_default_title", default='')
        powered_by = config.get_param(key="awesome_theme_pro.powered_by", default='')

        record = self.env["awesome_theme_pro.theme_setting_base"].search([('system', '=', True)])
        if not record:
            record = self.env["awesome_theme_pro.theme_setting_base"].create({
                "system": True
            })

        return {
            "layout_mode": layout_mode,
            "login_style": login_style,

            "theme_setting_mode": theme_setting_mode,
            "current_theme_mode": int(current_theme_mode),
            "current_theme_style": int(current_theme_style),
            "form_style": form_style,
            "multi_tab_mode": True if multi_tab_mode == 'True' else False,
            "dialog_pop_style": dialog_pop_style,
            "button_style": button_style,
            "control_panel_mode": control_panel_mode,
            "table_style": table_style,
            "font_name": font_name,
            "show_app_name": show_app_name,
            "rtl_mode": rtl_mode,
            "favorite_mode": favorite_mode,
            "pwa_name": record.pwa_name,
            "pwa_short_name": record.pwa_short_name,
            "pwa_background_color": record.pwa_background_color,
            "pwa_theme_color": record.pwa_theme_color,

            "window_default_title": window_default_title,
            "powered_by": powered_by,

            # "icon128_url": record.icon128_url,
            # "icon144_url": record.icon144_url,
            # "icon152_url": record.icon152_url,
            # "icon192_url": record.icon192_url,
            # "icon256_url": record.icon256_url,
            # "icon512_url": record.icon512_url,
        }

    @api.model
    def get_theme_setting_mode(self):
        '''
        get theme setting mode
        :return:
        '''
        config = self.env['ir.config_parameter'].sudo()
        theme_setting_mode = config.get_param(
            key='awesome_theme_pro.theme_setting_mode', default='system')
        return theme_setting_mode

    @api.model
    def get_theme_values(self):
        '''
        get the theme values
        :return:
        '''
        config = self.env['ir.config_parameter'].sudo()

        layout_mode = config.get_param(key='awesome_theme_pro.layout_mode', default='awesome_theme_pro.layout_mode1')
        login_style = config.get_param(key='awesome_theme_pro.login_style', default='login_style1')
        theme_setting_mode = config.get_param(key='awesome_theme_pro.theme_setting_mode', default='system')
        current_theme_mode = config.get_param(key='awesome_theme_pro.current_theme_mode', default=False)
        current_theme_style = config.get_param(key='awesome_theme_pro.current_theme_style', default=False)
        form_style = config.get_param(key='awesome_theme_pro.form_style', default='normal')
        multi_tab_mode = config.get_param(key="awesome_theme_pro.multi_tab_mode")
        dialog_pop_style = config.get_param(key="awesome_theme_pro.dialog_pop_style", default='normal')
        button_style = config.get_param(key="awesome_theme_pro.button_style", default='btn-style-normal')
        control_panel_mode = config.get_param(key="awesome_theme_pro.control_panel_mode", default='mode1')
        table_style = config.get_param(key="awesome_theme_pro.table_style", default='normal')
        font_name = config.get_param(key="awesome_theme_pro.font_name", default='Roboto')
        show_app_name = config.get_param(key="awesome_theme_pro.show_app_name", default=True)
        rtl_mode = config.get_param(key="awesome_theme_pro.rtl_mode", default=False)
        favorite_mode = config.get_param(key="awesome_theme_pro.favorite_mode", default=False)
        allow_debug = config.get_param(key="awesome_theme_pro.allow_debug", default=True)

        return {
            "layout_mode": layout_mode,
            "login_style": login_style,
            "theme_setting_mode": theme_setting_mode,
            "current_theme_mode": int(current_theme_mode),
            "current_theme_style": int(current_theme_style),
            "form_style": form_style,
            "multi_tab_mode": True if multi_tab_mode == 'True' else False,
            "dialog_pop_style": dialog_pop_style,
            "button_style": button_style,
            "control_panel_mode": control_panel_mode,
            "table_style": table_style,
            "font_name": font_name,
            "show_app_name": show_app_name,
            "rtl_mode": rtl_mode,
            "favorite_mode": favorite_mode,
            "allow_debug": allow_debug,
        }

    @api.model
    def get_values(self):
        '''
        get the vuales
        :return:
        '''
        res = super(AwesomeUserSetting, self).get_values()

        config = self.env['ir.config_parameter'].sudo()

        layout_mode = config.get_param(key='awesome_theme_pro.layout_mode', default='layout_mode1')
        login_style = config.get_param(key='awesome_theme_pro.login_style', default='login_style1')
        theme_setting_mode = config.get_param(key='awesome_theme_pro.theme_setting_mode', default='system')
        current_theme_mode = config.get_param(key='awesome_theme_pro.current_theme_mode', default=False)
        current_theme_style = config.get_param(key='awesome_theme_pro.current_theme_style', default=False)
        form_style = config.get_param(key='awesome_theme_pro.form_style', default='normal')
        multi_tab_mode = config.get_param(key="awesome_theme_pro.multi_tab_mode")
        dialog_pop_style = config.get_param(key="awesome_theme_pro.dialog_pop_style", default='normal')
        button_style = config.get_param(key="awesome_theme_pro.button_style", default='btn-style-normal')
        control_panel_mode = config.get_param(key="awesome_theme_pro.control_panel_mode", default='mode1')
        table_style = config.get_param(key="awesome_theme_pro.table_style", default='normal')
        font_name = config.get_param(key="awesome_theme_pro.font_name", default='Roboto')
        show_app_name = config.get_param(key="awesome_theme_pro.show_app_name", default=True)
        rtl_mode = config.get_param(key="awesome_theme_pro.rtl_mode", default=False)
        favorite_mode = config.get_param(key="awesome_theme_pro.favorite_mode", default=False)
        allow_debug = config.get_param(key="awesome_theme_pro.allow_debug", default=True)
        window_default_title = config.get_param(key="awesome_theme_pro.allow_debug", default="Awesome odoo")
        powered_by = config.get_param(key="awesome_theme_pro.powered_by", default="Awesome odoo")

        res.update(
            layout_mode=layout_mode,
            login_style=login_style,
            theme_setting_mode=theme_setting_mode,
            current_theme_mode=int(current_theme_mode),
            current_theme_style=int(current_theme_style),
            form_style=form_style,
            multi_tab_mode=bool(multi_tab_mode),
            dialog_pop_style=dialog_pop_style,
            button_style=button_style,
            control_panel_mode=control_panel_mode,
            table_style=table_style,
            font_name=font_name,
            show_app_name=show_app_name,
            rtl_mode=rtl_mode,
            allow_debug=allow_debug,
            favorite_mode=favorite_mode,
            powered_by=powered_by,
            window_default_title=window_default_title
        )

        return res

    def set_values(self):
        '''
        set values
        :return:
        '''
        super(AwesomeUserSetting, self).set_values()

        ir_config = self.env['ir.config_parameter'].sudo()

        ir_config.set_param("awesome_theme_pro.layout_mode", self.layout_mode or "layout_mode1")
        ir_config.set_param("awesome_theme_pro.login_style", self.login_style or "login_style1")
        ir_config.set_param("awesome_theme_pro.theme_setting_mode", self.theme_setting_mode or 'system')
        ir_config.set_param("awesome_theme_pro.current_theme_mode", self.current_theme_mode.id or False)
        ir_config.set_param("awesome_theme_pro.current_theme_style", self.current_theme_style.id or False)
        ir_config.set_param("awesome_theme_pro.form_style", self.form_style or 'normal')
        ir_config.set_param("awesome_theme_pro.multi_tab_mode", self.multi_tab_mode)
        ir_config.set_param("awesome_theme_pro.dialog_pop_style", self.dialog_pop_style or 'normal')
        ir_config.set_param("awesome_theme_pro.button_style", self.button_style or 'btn-style-normal')
        ir_config.set_param("awesome_theme_pro.table_style", self.table_style or 'normal')
        ir_config.set_param("awesome_theme_pro.control_panel_mode", self.control_panel_mode or 'normal')
        ir_config.set_param("awesome_theme_pro.font_name", self.font_name or 'Roboto')
        ir_config.set_param("awesome_theme_pro.show_app_name", self.show_app_name)
        ir_config.set_param("awesome_theme_pro.rtl_mode", self.rtl_mode)
        ir_config.set_param("awesome_theme_pro.favorite_mode", self.favorite_mode)
        ir_config.set_param("awesome_theme_pro.allow_debug", self.favorite_mode)

        ir_config.set_param("awesome_theme_pro.pwa_name", self.pwa_name)
        ir_config.set_param("awesome_theme_pro.pwa_short_name", self.pwa_short_name)
        ir_config.set_param("awesome_theme_pro.pwa_background_color", self.pwa_background_color)
        ir_config.set_param("awesome_theme_pro.pwa_theme_color", self.pwa_theme_color)

        ir_config.set_param("awesome_theme_pro.window_default_title", self.window_default_title)
        ir_config.set_param("awesome_theme_pro.powered_by", self.powered_by)

    def set_values_company_favicon(self):
        '''
        set the favicon of company
        :return:
        '''
        company = self.sudo().env['res.company']
        records = company.search([])

        if len(records) > 0:
            for record in records:
                record.write({'favicon': self._set_web_favicon(original=True)})

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def get_login_style(self):
        '''
        get login style
        :return:
        '''
        ir_config = self.env['ir.config_parameter'].sudo()
        login_style = ir_config.get_param(
            key='awesome_theme_pro.login_style', default='login_style1')
        return login_style

    @api.model
    def awesome_pwa_setting(self):
        """
        pwa setting
        :return:
        """
        form_id = self.env.ref('awesome_theme_pro.system_pwa_config').id
        record = self.env["awesome_theme_pro.theme_setting_base"].search([('system', '=', True)])
        if not record:
            record = self.env["awesome_theme_pro.theme_setting_base"].create({
                "system": True
            })

        return {
            "type": "ir.actions.act_window",
            "res_model": "awesome_theme_pro.theme_setting_base",
            'view_mode': 'form',
            "target": "new",
            "res_id": record.id,
            "views": [[form_id, "form"]]
        }

    def _set_web_favicon(self, original=False):
        '''
        set seb favicon
        :param original:
        :return:
        '''
        ir_config = self.env['ir.config_parameter'].sudo()
        favicon = ir_config.get_param('awesome_theme_pro.web_icon')
        if not favicon:
            img_path = get_resource_path('awesome_theme', 'static/src/img/favicon.png')
        else:
            img_path = get_resource_path('awesome_theme', favicon)

        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())

            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="ICO")
            return base64.b64encode(stream.getvalue())
