# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol Infotech Private Limited. (<https://www.droggol.com/>)
import json

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    d_mass_mailing_theme_colors = fields.Char(string="Theme Colors", default='{"primary": "#4285f4", "secondary": "#f3f5f9", "info": "#33b5e5", "warning": "#ffbb33", "danger": "#ff3547", "header": "#333333", "content": "#737373"}', config_parameter='d_mass_mailing_theme_colors')

    def set_values(self):
        old_palette = self.env['ir.config_parameter'].get_param('d_mass_mailing_theme_colors')
        super(ResConfigSettings, self).set_values()
        new_palette = self.env['ir.config_parameter'].get_param('d_mass_mailing_theme_colors')
        if old_palette != new_palette:
            url = '/droggol_mass_mailing_themes/static/src/scss/themes/_drgl_theme_variable.scss'
            bundle_id = 'mass_mailing.assets_mail_themes'
            palette = json.loads(new_palette)
            content = '\n'.join(['$o-mm-prime-color-'+k+':'+v+';' for k, v in palette.items()])
            WebEditorAssets = self.env['web_editor.assets']
            WebEditorAssets.save_asset(url, bundle_id, content, 'scss')

            # Clear website id from view and attachment
            custom_url = WebEditorAssets.make_custom_asset_file_url(url, bundle_id)
            attachment = WebEditorAssets._get_custom_attachment(custom_url)
            if 'website_id' in attachment._fields:
                attachment.website_id = False

            view = WebEditorAssets._get_custom_view(custom_url)
            if 'website_id' in attachment._fields:
                view.with_context(no_cow=True).website_id = False

    def dr_mm_clean_internal(self):
        WebEditorAssets = self.env['web_editor.assets']

        url = '/droggol_mass_mailing_themes/static/src/scss/themes/_drgl_theme_variable.scss'
        bundle_id = 'mass_mailing.assets_mail_themes'

        custom_url = WebEditorAssets.make_custom_asset_file_url(url, bundle_id)
        attachment = WebEditorAssets._get_custom_attachment(custom_url)
        view = WebEditorAssets._get_custom_view(custom_url)

        # Delete the custom attachment
        if attachment:
            attachment.unlink()

        # Delete the custom views
        if view:
            view.with_context(no_cow=True).unlink()

        # Delete config params
        config = self.env['ir.config_parameter'].search([('key', '=', 'd_mass_mailing_theme_colors')])
        if config:
            config.unlink()
