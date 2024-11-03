# from attr import field
from odoo import models,api,fields


class nineBoxGrid(models.Model):
    _name = 'nine.box.grid'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char()
    description = fields.Text()
    suggestion_action = fields.Text()