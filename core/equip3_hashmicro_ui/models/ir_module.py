from odoo import models

XML_ID = "equip3_hashmicro_ui._assets_primary_variables"
SCSS_URL = "/equip3_hashmicro_ui/static/src/scss/colors.scss"

class IrModule(models.Model):
    _inherit = 'ir.module.module'

    def button_upgrade(self):
        result = super(IrModule, self).button_upgrade()
        custom_url = self.env['equip3_hashmicro_ui.scss_editor']._get_custom_url(SCSS_URL, XML_ID)
        custom_attachment = self.env['equip3_hashmicro_ui.scss_editor']._get_custom_attachment(custom_url)
        if custom_attachment.exists():
            custom_attachment.unlink()
        config_id = self.env['sh.back.theme.config.settings'].sudo().search([], limit=1)
        if config_id:
            self.env['res.users'].change_theme_color({'color': config_id.equip_theme_color})
        return result
