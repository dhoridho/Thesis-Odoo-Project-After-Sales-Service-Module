from odoo import models,api,fields


class MasterWaTemplate(models.Model):
    _inherit = 'master.template.message'
    
    is_accounting = fields.Boolean(default=False)