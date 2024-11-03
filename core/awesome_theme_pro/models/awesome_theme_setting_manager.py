# -*- coding: utf-8 -*-

from odoo import models, api


class AwesomeThemeSettingManager(models.AbstractModel):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.theme_setting_manager'
    _description = 'theme setting manager'

    @api.model
    def get_user_setting(self, get_mode_data=True, get_style_txt=True):
        '''
        get user setting
        :return:
        '''
        rst = dict()

        theme_setting_mode = \
            self.env["res.config.settings"].sudo().get_theme_setting_mode()

        # check mode data
        owner = False
        if theme_setting_mode == 'system':
            owner = False
        elif theme_setting_mode == 'company':
            owner = 'res.company, {company_id}'.format(
                company_id=self.env.user.company_id.id)
        elif theme_setting_mode == 'user':
            owner = 'res.users, {user_id}'.format(user_id=self.env.user.id)

        # check theme mode data
        self.env["awesome_theme_pro.theme_mode"].check_default_mode_data(owner)

        if theme_setting_mode == 'system':
            theme_settings = self.env["res.config.settings"].get_theme_setting()
        elif theme_setting_mode == 'company':
            theme_settings = self.env["res.company"].get_theme_setting()
        else:
            theme_settings = self.env["res.users"].get_theme_setting()

        all_modes = self.env["awesome_theme_pro.theme_mode"].search([('owner', '=', owner)])

        cur_style_id = theme_settings["current_theme_style"]
        cur_mode_id = theme_settings["current_theme_mode"]

        theme_mode = self.env["awesome_theme_pro.theme_mode"].browse(cur_mode_id)
        theme_style = self.env["awesome_theme_pro.theme_style"].browse(cur_style_id)

        if not cur_mode_id or cur_mode_id not in all_modes.ids or not theme_style:
            cur_mode_id = all_modes[0].id
            cur_style_id = all_modes[0].theme_styles[0].id

        theme_style = self.env["awesome_theme_pro.theme_style"].browse(cur_style_id)

        if get_mode_data:
            rst['theme_modes'] = all_modes.get_mode_data()

        rst['settings'] = theme_settings
        rst['cur_mode_id'] = cur_mode_id
        rst['cur_style_id'] = cur_style_id

        rst["window_default_title"] = self.env['ir.config_parameter'].sudo().get_param(
            "awesome_theme_pro.window_default_title", "Awesome Odoo")
        rst["powered_by"] = self.env['ir.config_parameter'].sudo().get_param(
            "awesome_theme_pro.powered_by", "Awesome Odoo")

        # check the user is admin
        rst['is_admin'] = self.env.user._is_admin()

        # add font info
        font_name = theme_settings.get("font_name", False)
        if font_name:
            font_type_css = "*:not(.fa) {font-family: " + font_name + ", sans-serif !important;}"
        else:
            font_type_css = ""

        # get the style
        if get_style_txt:
            style_data_vec = [font_type_css]
            if theme_style:
                style_data_vec = theme_style.get_styles_txt()

            style_txt = '\n'.join(style_data_vec)
            rst['style_txt'] = style_txt

        # get the mode style
        if get_style_txt:
            if theme_mode.name != 'normal':
                mode_style_css = theme_mode.compiled_mode_style_css
                rst['mode_style_css'] = mode_style_css

        return rst

    @api.model
    def update_cur_style(self, mode_id, style_id):
        '''
        update user cur mode
        :return:
        '''
        ir_config = self.env['ir.config_parameter'].sudo()
        setting_mode = self.env["res.config.settings"].get_theme_setting_mode()
        if setting_mode == "system":
            ir_config.set_param("awesome_theme_pro.current_theme_mode", mode_id)
            ir_config.set_param("awesome_theme_pro.current_theme_style", style_id)
        elif setting_mode == "company":
            company_id = self.env.user.company_id
            company = self.env["res.company"].browse(company_id)
            company.setting_id.current_theme_mode = mode_id
            company.setting_id.current_theme_style = style_id
        elif setting_mode == "user":
            user_id = self.env.user.id
            user = self.env["res.users"].browse(user_id)
            user.setting_id.current_theme_mode = mode_id
            user.setting_id.current_theme_style = style_id
        else:
            assert False

    @api.model
    def save_style_data(self, style_id, style_data, editor_type):
        '''
        save style datas
        :param style_id:
        :param style_data:
        :param editor_type:
        :return:
        '''
        theme_style = self.env["awesome_theme_pro.theme_style"].browse(style_id)
        theme_style.ensure_one()

        theme_setting_mode = \
            self.env["res.config.settings"].sudo().get_theme_setting_mode()

        # save current style just when type is same
        if theme_setting_mode == editor_type:
            # update current style id
            mode_id = theme_style.theme_mode.id
            self.update_cur_style(mode_id, style_id)

        var_infos = theme_style.mapped('groups.sub_groups.style_items.vars')
        var_cache = {var_info.id: var_info for var_info in var_infos}
        for data in style_data:
            var_id = data["id"]
            tmp_var = var_cache[var_id]
            tmp_var.write({
                "color": data.get('color', False),
                "image": data.get('image', False),
                "svg": data.get('svg', False)
            })
        # return the style data
        return theme_style.get_style()

    def get_current_owner(self):
        """
        get current owner
        :return:
        """
        theme_setting_mode = \
            self.env["res.config.settings"].sudo().get_theme_setting_mode()

        # check mode data
        owner = False
        if theme_setting_mode == 'system':
            owner = False
        elif theme_setting_mode == 'company':
            owner = 'res.company, {company_id}'.format(
                company_id=self.env.user.company_id.id)
        elif theme_setting_mode == 'user':
            owner = 'res.users, {user_id}'.format(user_id=self.env.user.id)

        return owner
