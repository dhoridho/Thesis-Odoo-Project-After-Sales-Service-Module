
from odoo import api,models
import odoo

class IRConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    @api.model
    def get_hide_traceback(self):
        hide_traceback = odoo.tools.config.get('hide_traceback',False)
        return hide_traceback


  