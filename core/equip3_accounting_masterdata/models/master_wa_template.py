from odoo import models,api,fields


class equip3MasterMessageTemplate(models.Model):
    _inherit = 'master.template.message'
    
    is_accounting = fields.Boolean(default=False)