from odoo import api, fields, models, _


class ResCity(models.Model):
    _name = 'res.country.city'
    _description = 'Res Country City'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char()
    city_code = fields.Char()
    state_id = fields.Many2one('res.country.state')
    
    
    
