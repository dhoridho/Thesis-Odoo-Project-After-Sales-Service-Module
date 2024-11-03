from odoo import api, fields, models, _

class ActiveLocation(models.Model):
    _name = 'active.location'

    employee_id = fields.Many2one('hr.employee')
    active_location_id = fields.Many2one('res.partner', string="Active Location")
    is_default = fields.Boolean(string="Default")