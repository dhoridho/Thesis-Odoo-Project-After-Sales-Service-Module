from odoo import fields,models

class equip3EmployeeMaritalStatus(models.Model):
    _name = 'employee.marital.status'
    _inherit = ['mail.thread','mail.activity.mixin']
    name = fields.Char()
