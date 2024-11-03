# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .awesome_theme_mode_template import template as awesome_mode_template
from .awesome_theme_mode_custom_template import template as awesome_mode_custom_template
import json
from odoo.tools import config

from ..models.awesome_dark_mode.awesome_dark_vars import default_vars as dark_vars
from ..models.awesome_blue_mode.awesome_blue_vars import default_vars as blue_vars
from ..models.awesome_green_mode.awesome_green_vars import default_vars as green_vars

DEFAULT_VARS = {
    # three background color
    '$light_background_color': '#03655c',
    '$light_dark_background_color': '#03655c',
    '$dark_background_color': '#034e47',

    '$text_color': '#fff',

    # primary
    '$primary_color': '#034e47',
    '$primary_hover_color': '#03655c',
    '$primary_active_color': '#03655c',

    # border
    '$primary_border_color': '#033e38',
    '$primary_border_hover_color': '#033e38',
    '$primary_border_active_color': '#033e38',

    # text
    '$primary_text_color': '#c7c7c7',
    '$primary_text_hover_color': '#fff',
    '$primary_text_active_color': '#fff',

    # secondary
    '$secondary_color': '#03655c',
    '$secondary_hover_color': '#03544d',
    '$secondary_active_color': '#4d5ed6',

    # secondary border
    '$secondary_border_color': '#034e47',
    '$secondary_border_hover_color': '#03655c',
    '$secondary_border_active_color': '#03655c',

    # secondary text
    '$secondary_text_color': '#c7c7c7',
    '$secondary_text_hover_color': '#fff',
    '$secondary_text_active_color': '#fff',

    # other
    '$dark_border_color': '#03655c',
    '$light_border_color': '#03655c',

    # menu item
    '$menu_item_color': '#1f2b73',
    '$menu_item_hover_color': '#1f2b73',

    # text color
    '$menu_item_text_color': '#aab3f4',
    '$menu_item_hover_text_color': '#fff',

    # shadow
    '$shadow_color': 'rgba(33,37,41,0.67)',

    # link
    '$link_color': '#313852',
    '$link_active_color': '#0a6b62',
    '$link_hover_color': '#0a6b62',

    '$link_text_color': '#c7c7c7',
    '$link_text_hover_color': '#c7c7c7',
    '$link_text_active_text_color': '#c7c7c7',

    # table
    '$table_row_hover_color': 'rgba(33,37,41,0.67)',
    '$table_text_color': '#c7c7c7',
    '$table_border_color': '#4d5075',
    '$table_row_color': 'rgba(33,37,41,0.67)',
    '$table_odd_row_color': 'rgba(0,0,0,0.1)'
}


class AwesomeThemeModeWizard(models.TransientModel):
    """
    akl theme mode wizard
    """
    _name = 'awesome_theme_pro.theme_mode_wizard'
    _description = 'file replace wizard'

    name = fields.Char(string="name", required=True)
    owner = fields.Char(string="owner")
    theme_mode = fields.Many2one(comodel_name="awesome_theme_pro.theme_mode", string="theme_mode")
    apply_vars_to_styles = fields.Boolean(string="apply vars to styles", default=False)
    color_vars = fields.One2many(
        comodel_name='awesome_theme_pro.color_var',
        inverse_name="wizard",
        default=lambda self: self._get_default_val())

    @api.model
    def _get_default_val(self):
        """
        get default vars
        :return:
        """
        return [(0, 0, {'name': name, 'val': DEFAULT_VARS[name]}) for name in DEFAULT_VARS]

    def create_mode(self):
        """
        btn action
        """
        color_vars = self.color_vars

        # css template data
        mode_json_text = awesome_mode_template.replace('$mode_name', self.name)
        for tmp_var in color_vars:
            mode_json_text = str(mode_json_text).replace(tmp_var.name, tmp_var.val)

        # custom items
        mode_custom_json_txt = awesome_mode_custom_template
        for tmp_var in color_vars:
            mode_custom_json_txt = str(mode_custom_json_txt).replace(tmp_var.name, tmp_var.val)

        # create mode data
        mode_data = json.loads(mode_custom_json_txt)
        owner = self.env["awesome_theme_pro.theme_setting_manager"].get_current_owner()
        record = self.env["awesome_theme_pro.theme_mode"].create_mode({
            "theme_styles": [mode_data],
            "name": self.name,
            "version": '1.0.0.1'
        }, owner=owner, is_default=False)

        # set mode json text
        record.mode_style_css = mode_json_text

        # save mode vars
        tmp_vars = {tmp_var.name: tmp_var.val for tmp_var in color_vars}
        record.mode_vars = json.dumps(tmp_vars)

        # return the mode data
        return record.get_mode_data()

    def update_mode(self):
        """
        btn action
        """
        color_vars = self.color_vars

        # css template data
        mode_json_text = awesome_mode_template.replace('$mode_name', self.name)
        for tmp_var in color_vars:
            mode_json_text = str(mode_json_text).replace(tmp_var.name, tmp_var.val)
        self.theme_mode.mode_style_css = mode_json_text
        self.theme_mode.compute_mode_style()

        mode_vars = {tmp_var.name: tmp_var.val for tmp_var in color_vars}
        self.theme_mode.mode_vars = json.dumps(mode_vars)

        # return the mode data
        return self.theme_mode.get_mode_data()

    def preview_mode(self):
        """
        btn action
        """
        color_vars = self.color_vars

        # custom items
        mode_custom_json_txt = awesome_mode_custom_template
        for tmp_var in color_vars:
            mode_custom_json_txt = str(mode_custom_json_txt).replace(tmp_var.name, tmp_var.val)

        # css template data
        mode_style_txt = awesome_mode_template.replace('$mode_name', "mode_preview")
        for tmp_var in color_vars:
            mode_style_txt = str(mode_style_txt).replace(tmp_var.name, tmp_var.val)

        mode_style_txt = self.env["awesome_theme_pro.theme_mode"]._compile_scss(mode_style_txt)
        mode_style_txt = mode_style_txt.replace(
            'body.{name}'.format(name=self.name), "body.mode_preview")

        # return the mode data
        return mode_style_txt

    @api.model
    def get_change_mode_setting_wizard(self, mode_id):
        """
        get change mode setting wizard
        :return:
        """
        theme_mode = self.env["awesome_theme_pro.theme_mode"].browse(mode_id)
        mode_vars = theme_mode.mode_vars
        mode_vars = json.loads(mode_vars or "{}")
        default_vars = [(0, 0, {'name': name, 'val': mode_vars[name]}) for name in mode_vars]

        if config.options.get('local_debug', False):
            if theme_mode.name == 'dark':
                default_vars = [(0, 0, {'name': name, 'val': dark_vars[name]}) for name in dark_vars]
            elif theme_mode.name == 'green':
                default_vars = [(0, 0, {'name': name, 'val': green_vars[name]}) for name in green_vars]
            elif theme_mode.name == 'blue':
                default_vars = [(0, 0, {'name': name, 'val': blue_vars[name]}) for name in blue_vars]

        return {
            "type": "ir.actions.act_window",
            "res_model": "awesome_theme_pro.theme_mode_wizard",
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': theme_mode.name,
                'default_color_vars': default_vars,
                'default_theme_mode': mode_id
            },
            "views": [[self.env.ref('awesome_theme_pro.theme_mode_wizard').id, "form"]]
        }


class ColorVar(models.TransientModel):
    """
    color item
    """
    _name = 'awesome_theme_pro.color_var'
    _description = 'color var'

    wizard = fields.Many2one(
        'awesome_theme_pro.theme_mode_wizard', string='wizard', ondelete='cascade')
    name = fields.Char(string='name')
    val = fields.Char(string='val')
