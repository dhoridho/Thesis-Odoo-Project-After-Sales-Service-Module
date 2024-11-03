from odoo import fields,api,models

class jobCategory(models.Model):
    _name = 'job.category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Job Category'
    
    
    name = fields.Char()
    description = fields.Text()