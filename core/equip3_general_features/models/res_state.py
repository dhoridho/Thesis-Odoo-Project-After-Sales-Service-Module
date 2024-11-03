from odoo import api, fields, models, _


class ResCountryStateGeneralSetting(models.Model):
    _inherit = 'res.country.state'
    city_ids = fields.One2many('res.country.city','state_id')
    
    
    
    
   