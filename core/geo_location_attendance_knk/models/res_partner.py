from odoo import models,fields


class restPartner(models.Model):
    _inherit = 'res.partner'
    
    attendance_range = fields.Integer(string='Attendance Range')
    