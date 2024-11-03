from odoo import api, fields, models


class IstMindsetProfile(models.Model):
    _name = 'ist.mindset.profile'

    name = fields.Char(string='Name')
    description = fields.Char()
    is_verbal_teoritis = fields.Boolean(default=False)
    
