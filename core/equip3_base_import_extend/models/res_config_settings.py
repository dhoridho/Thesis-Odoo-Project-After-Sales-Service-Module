from odoo import api, fields, models
from datetime import datetime, timedelta


class baseImportExtendSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    test_import_batch_limit = fields.Integer(config_parameter='equip3_base_import_extend.test_import_batch_limit',default=10)
    is_split_processing = fields.Boolean(config_parameter='equip3_base_import_extend.is_split_processing',default=False)
    last_proggress_data = fields.Integer(config_parameter='equip3_base_import_extend.last_proggress_data',default=5)
    limit_split_line_import = fields.Integer(config_parameter='equip3_base_import_extend.limit_split_line_import',default=1000)
    

    @api.model
    def get_values(self):
        res = super(baseImportExtendSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        test_import_batch_limit = ICPSudo.get_param('equip3_base_import_extend.test_import_batch_limit')
        res.update(test_import_batch_limit=test_import_batch_limit)
        return res

    def set_values(self):
        super(baseImportExtendSettings, self).set_values()
        for rec in self:
            ICPSudo = rec.env['ir.config_parameter'].sudo()
            test_import_batch_limit = rec.test_import_batch_limit
            last_proggress_data = rec.last_proggress_data
            limit_split_line_import = rec.limit_split_line_import
            if test_import_batch_limit == 0:
                test_import_batch_limit = 10
                
            if last_proggress_data == 0:
                last_proggress_data = 5    
                     
            ICPSudo.set_param('equip3_base_import_extend.test_import_batch_limit',test_import_batch_limit)
            ICPSudo.set_param('equip3_base_import_extend.last_proggress_data',last_proggress_data)
            ICPSudo.set_param('equip3_base_import_extend.limit_split_line_import',limit_split_line_import)