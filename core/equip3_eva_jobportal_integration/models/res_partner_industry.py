from odoo import fields,api,models

class resPartnerIndustry(models.Model):
    _name = 'res.partner.industry'
    _inherit = ['res.partner.industry','mail.thread', 'mail.activity.mixin']
    _description = 'Indusry'
    
