# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .awesome_theme_default_data import default_modes, version
import json
from odoo.modules.module import get_resource_path
from ..wizard.awesome_theme_mode_template import template as awesome_mode_template
from odoo.tools import config
from ..models.awesome_dark_mode.awesome_dark_mode import dark_mode
from ..models.awesome_blue_mode.awesome_blue_mode import blue_mode
from ..models.awesome_green_mode.awesome_green_mode import green_mode


try:
    import sass as libsass
except ImportError:
    libsass = None


class AwesomeThemeMode(models.Model):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.theme_mode'
    _description = 'awesome theme mode'

    name = fields.Char(string="name", required=True)

    sequence = fields.Integer(string="mode sequence", default=0)

    theme_styles = fields.One2many(
        string="theme styles",
        comodel_name="awesome_theme_pro.theme_style",
        inverse_name="theme_mode")

    is_default = fields.Boolean(
        string="is default", default=True)

    # if owner is False, so the style own to global
    owner = fields.Reference(
        string="owner",
        selection=[('res.company', 'res.company'), ('res.users', 'res.users')],
        default=False,
        help="owner which this theme is create by")

    mode_style_css = fields.Text(string="mode style css")
    compiled_mode_style_css = \
        fields.Text(string="compiled mode style css", compute="compute_mode_style", store=True)
    mode_vars = fields.Text(string="default vars")
    version = fields.Char(string="version")

    _sql_constraints = [('theme_mode_name_unique', 'UNIQUE(name)', "theme mode name must unique")]

    def get_mode_preview_data(self):
        """
        get mode preview data
        :return:
        """
        # for debug
        if config.options.get('local_debug', False):
            style_txt = None
            if self.name == "dark":
                style_txt = self.get_default_mode_style_text(dark_mode)
            elif self.name == "blue":
                style_txt = self.get_default_mode_style_text(blue_mode)
            elif self.name == "green":
                style_txt = self.get_default_mode_style_text(green_mode)

            if style_txt:
                mode_style_css = self._compile_scss(style_txt)
                mode_style_css = mode_style_css.replace(
                    'body.{name}'.format(name=self.name), "body.mode_preview")

                return mode_style_css

        if self.mode_style_css:
            if not self.compiled_mode_style_css:
                self.compute_mode_style()
            mode_style_css = self.compiled_mode_style_css.replace(
                'body.{name}'.format(name=self.name), "body.mode_preview")
            return mode_style_css
        else:
            return ""

    @api.model
    def compute_mode_style(self):
        """
        compute mode style
        :return:
        """
        for record in self:
            if self.mode_style_css:
                record.compiled_mode_style_css = self._compile_scss(self.mode_style_css)

    def _compile_scss(self, mode_style_css):
        """
        This code will compile valid scss into css.
        Simply copied and adapted slightly
        """
        scss_source = mode_style_css.strip()
        if not scss_source:
            return ""

        precision = 8
        output_style = 'expanded'
        scss_path = get_resource_path('awesome_theme_pro', 'static', 'css', 'common')

        try:
            return libsass.compile(
                string=scss_source,
                include_paths=[
                    scss_path,
                ],
                output_style=output_style,
                precision=precision,
            )
        except libsass.CompileError as e:
            raise libsass.CompileError(e.args[0])

    @api.model
    def compute_mode_style_url(self):
        """
        compute mode style url
        :return:
        """
        for record in self:
            record.mode_style_url = \
                '/web/image/akl_theme.theme_setting_base/{var_id}/icon128x128'.format(
                    var_id=record.id)

    def get_default_mode_style_text(self, theme_mode_info):
        """
        get default mode data
        :return:
        """
        if self.name == 'normal':
            return

        color_vars = theme_mode_info["default_vars"]
        # css template data
        mode_json_text = awesome_mode_template.replace('$mode_name', self.name)
        for var_nam in color_vars:
            mode_json_text = str(mode_json_text).replace(var_nam, color_vars[var_nam])
        return mode_json_text

    def check_default_mode_data(self, owner=False):
        '''
        check default mode data
        :return:
        '''
        modes = self.search([('owner', '=', owner)])
        mode_names = modes.mapped('name')

        # create new mode
        for model_name in default_modes:
            if model_name not in mode_names:
                default_mode = default_modes[model_name]

                # create new mode use the mode data
                record = self.create_mode(default_mode, owner)
                if model_name == "normal":
                    continue

                # set mode json text
                mode_json_text = record.get_default_mode_style_text(default_mode)
                record.mode_style_css = mode_json_text

                # save mode vars
                color_vars = default_mode["default_vars"]
                record.mode_vars = json.dumps(color_vars)

        # check mode data
        for theme_mode in modes:
            # ignore if version is not changed
            if theme_mode.version == version:
                continue
            theme_mode.check_mode_data()

    def create_mode(self, model_data, owner=False, is_default=True):
        '''
        create mode
        :param mode_style_txt:
        :param model_data:
        :param owner:
        :param is_default:
        :return:
        '''
        theme_styles = model_data['theme_styles']
        theme_style_array = []
        for theme_style in theme_styles:
            groups = theme_style["groups"]
            group_datas = []
            for group_index, group in enumerate(groups):
                sub_groups = group["sub_groups"]
                var_index = 0
                item_index = 0
                sub_group_array = []
                for sub_group_index, sub_group in enumerate(sub_groups):
                    # create sub group
                    item_array = []
                    style_items = sub_group["style_items"]
                    for style_item in style_items:
                        var_val_array = []
                        var_infos = style_item["vars"]
                        for var_info in var_infos:
                            var_val_array.append((0, 0, {
                                "name": var_info["name"],
                                "is_default": True,
                                "type": var_info["type"],
                                "sequence": var_index,
                                "color": var_info.get('color', False),
                                "image": var_info.get('image', False),
                                "image_url": var_info.get('image_url', False),
                                "svg": var_info.get('svg', False),
                                "identity": var_info.get('identity', False)
                            }))
                            var_index += 1
                        item_array.append((0, 0, {
                            "name": style_item["name"],
                            "is_default": True,
                            "sequence": item_index,
                            "val_template": style_item["val_template"],
                            "sub_group": sub_group["name"],
                            "vars": var_val_array,
                            "selectors": json.dumps(style_item["selectors"])
                        }))
                        item_index += 1
                    sub_group_array.append((0, 0, {
                        "name": sub_group["name"],
                        "sequence": sub_group_index,
                        "style_items": item_array,
                        "is_default": True
                    }))
                group_datas.append((0, 0, {
                    "name": group["name"],
                    "sequence": group_index,
                    "is_default": True,
                    "sub_groups": sub_group_array
                }))

            theme_style_array.append((0, 0, {
                "name": theme_style["name"],
                "is_default": theme_style["is_default"],
                "groups": group_datas
            }))

        return self.env["awesome_theme_pro.theme_mode"].create([{
            "name": model_data["name"],
            "theme_styles": theme_style_array,
            "version": version,
            "is_default": is_default,
            "owner": owner
        }])

    def get_mode_data(self):
        '''
        get the mode data
        :return:
        '''
        rst = []
        for record in self:
            tmp_data = record.read(['name', 'is_default', 'sequence', 'version'])[0]
            tmp_data['theme_styles'] = record.theme_styles.get_styles()
            rst.append(tmp_data)

        return rst

    def delete_mode(self):
        """
        delete the mode
        :return:
        """
        self.unlink()

    def check_mode_data(self):
        '''
        check the mode data
        :return:
        '''
        self.ensure_one()

        mode_name = self.name
        if mode_name not in default_modes:
            return

        theme_styles = self.theme_styles
        theme_style_names = theme_styles.mapped('name')

        default_mode = default_modes[mode_name]
        default_theme_styles = default_mode['theme_styles']
        for tmp_theme_style in default_theme_styles:
            # create new style
            style_name = tmp_theme_style['name']
            if style_name not in theme_style_names:
                self.env["awesome_theme_pro.theme_style"].create_style_from_default_data(
                    self.id, tmp_theme_style)
            else:
                # check the style data, may be one more style with the same name
                for theme_style in theme_styles:
                    theme_style.check_groups(tmp_theme_style["groups"])
