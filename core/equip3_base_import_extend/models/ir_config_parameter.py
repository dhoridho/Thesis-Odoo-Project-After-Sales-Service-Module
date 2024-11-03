
from odoo import api,models

class IRConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    @api.model
    def set_test_import_batch_limit(self):
        batch_limit = self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.test_import_batch_limit')
        if int(batch_limit) == 0:
            self.env['ir.config_parameter'].sudo().set_param('equip3_base_import_extend.test_import_batch_limit',10)


    @api.model
    def set_limit_split_line_import(self):
        batch_limit = self.env['ir.config_parameter'].sudo().get_param('equip3_base_import_extend.limit_split_line_import')
        if int(batch_limit) == 0:
            self.env['ir.config_parameter'].sudo().set_param('equip3_base_import_extend.limit_split_line_import',1000)