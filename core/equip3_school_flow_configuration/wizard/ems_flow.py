from odoo import api, models, fields, _

class EMSFlow(models.TransientModel):
    _name = 'ems.flow.wizard'
    
    name = fields.Char(string='Name', default='EMS Flow')