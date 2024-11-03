from odoo import api, fields, models, _


class HrEmployeeAddress(models.Model):
    _name = 'hr.employee.address'
    _description = 'Address Employee'
    employee_id = fields.Many2one('hr.employee')
    sequence = fields.Integer()
    address_type = fields.Selection([('current','Current Address'),('identity','Identity Address')])
    street = fields.Char()
    location  = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    postal_code = fields.Char()
    tel_number = fields.Char()
    