# -*- coding: utf-8 -*-

from odoo import fields, models
import base64
from datetime import date, datetime
from odoo.modules.module import get_resource_path


class AwesomeCompany(models.Model):
    '''
    extend to support current mode and current style
    '''
    _inherit = "res.company"
    _name = 'res.company'
    _inherits = {"awesome_theme_pro.theme_setting_base": "setting_id"}

    setting_id = fields.Many2one(
        comodel_name="awesome_theme_pro.theme_setting_base",
        required=True,
        ondelete="cascade",
        string="setting id")

    def _get_default_small_logo(self):
        '''
        get the default small logo
        :return:
        '''
        tmp_path = get_resource_path(
            'awesome_theme_pro', 'static', 'images', 'res_company_small_logo.png')
        return base64.b64encode(open(tmp_path, 'rb') .read())

    logo_small = fields.Binary(
        default=_get_default_small_logo, string="Company Small Logo")

    def get_mode_data(self):

        '''
        get mode data
        :return:
        '''
        owner = 'res.company, {company_id}'.format(
            company_id=self.env.user.company_id)
        if not self.theme_modes:
            # create theme mode from default data
            self.env["awesome_theme_pro.theme_mode"].check_default_mode_data(owner)
        return self.env["awesome_theme_pro.theme_mode"].get_mode_data()

    def get_company_mode_data(self):
        '''
        get company mode data
        :return:
        '''
        owner = 'res.company, {company_id}'.format(
            company_id=self.id)
        if not self.theme_modes:
            # create theme mode from default data
            self.env["awesome_theme_pro.theme_mode"].check_default_mode_data(owner)
        return self.env["awesome_theme_pro.theme_mode"].get_mode_data()

    def check_setting_id(self):
        '''
        check setting id
        :return:
        '''
        self.ensure_one()

        if not self.setting_id:
            # copy use the global default data
            values = self.env['res.config.settings'].get_theme_values()
            del values["theme_setting_mode"]
            del values["current_theme_mode"]
            del values["current_theme_style"]
            values["first_visited"] = True
            tmp_record = self.env["awesome_theme_pro.theme_setting_base"].create(values)
            self.setting_id = tmp_record.id

        if not self.setting_id.inited.first_visited:
            values = self.env['res.config.settings'].get_theme_values()
            del values["theme_setting_mode"]
            del values["current_theme_mode"]
            del values["current_theme_style"]
            values["first_visited"] = True
            self.setting_id.write(values)

    def get_theme_setting(self):
        '''
        get company setting
        :return:
        '''
        company_id = self.env.user.company_id.id
        record = self.search([('id', '=', company_id)])
        record.check_setting_id()
        field_names = [name for name, field in record.setting_id._fields.items() if name not in [
                "icon128x128", "icon144x144", "icon152x152", "icon192x192", "icon256x256", "icon512x512"]]
        result = record.setting_id.read(fields=field_names)[0]
        result["current_theme_mode"] = record.setting_id.current_theme_mode.id
        result["current_theme_style"] = record.setting_id.current_theme_style.id
        for key, item in result.items():
            if isinstance(item, datetime):
                result[key] = fields.Datetime.to_string(item)
            if isinstance(item, date):
                result[key] = fields.Date.to_string(item)

        return result

    def save_company_settings(self, settings):
        '''
        save settings to company id
        :param company_id:
        :param settings:
        :return:
        '''
        self.setting_id = (6, 0, settings)

    def edit_company_theme(self):
        '''
        edit company theme
        :return:
        '''
        self.ensure_one()

        rst = dict()

        # check mode data
        owner = 'res.company, {company_id}'.format(company_id=self.id)
        self.env["awesome_theme_pro.theme_mode"].check_default_mode_data(owner)

        theme_settings = self.get_theme_setting()
        cur_style_id = theme_settings["current_theme_style"]
        cur_mode_id = theme_settings["current_theme_mode"]

        all_modes = self.env["awesome_theme_pro.theme_mode"].search([('owner', '=', owner)])
        if not cur_mode_id:
            cur_mode_id = all_modes[0].id
            cur_style_id = all_modes[0].theme_styles[0].id

        rst['theme_modes'] = all_modes.get_mode_data()
        rst['settings'] = theme_settings
        rst['cur_mode_id'] = cur_mode_id
        rst['cur_style_id'] = cur_style_id
        rst['is_admin'] = self.env.is_admin()
        rst['owner'] = owner
        rst['editor_type'] = 'company'

        return {
            "type": "ir.actions.client",
            "tag": "theme_edit_action",
            "params": rst
        }

