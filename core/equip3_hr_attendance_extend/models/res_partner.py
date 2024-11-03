from odoo import models,api,fields

class resPartner(models.Model):
    _inherit = 'res.partner'
    
    is_use_att_reason = fields.Boolean(default=False)
    
    