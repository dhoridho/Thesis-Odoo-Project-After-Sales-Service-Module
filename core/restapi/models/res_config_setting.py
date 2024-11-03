
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import config


class ResConfigSettingsApi(models.TransientModel):
    _inherit = 'res.config.settings'
    
    
    def get_default_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('restapi.api_url')
        return base_url
        
class IRConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    @api.model
    def set_api_url_values(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        api_url  = self.env['ir.config_parameter'].sudo().get_param('restapi.api_url')
        cek = str(base_url).split(":")
        if not api_url:
            if len(cek) > 2:
                self.env['ir.config_parameter'].sudo().set_param('restapi.api_url',f"{base_url}")
            else:
                self.env['ir.config_parameter'].sudo().set_param('restapi.api_url',f"{base_url}:{config.get('http_port')}")