from odoo import _, api, fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    marital = fields.Many2one('employee.marital.status', string='Marital Status')

class User(models.Model):
    _inherit = ['res.users']

    marital = fields.Many2one(related='employee_id.marital', readonly=False, related_sudo=False)