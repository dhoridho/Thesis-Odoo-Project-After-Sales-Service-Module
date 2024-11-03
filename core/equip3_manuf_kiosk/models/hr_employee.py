from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # duplicated from equip3_hr_masterdata_employee
    sequence_code = fields.Char(string="Employee ID")
