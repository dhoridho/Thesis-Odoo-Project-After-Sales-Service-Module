from odoo import _, api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class EmployeeBankAccount(models.Model):
    _name = 'bank.account'
    is_used = fields.Boolean("Primary Account")
    name = fields.Many2one('res.bank',"Name Of Bank")
    bic = fields.Char(related='name.bic',string="Bank Identifier Code")
    bank_unit = fields.Char(string="KCP / Unit")
    acc_number = fields.Char("Account Number")
    acc_holder = fields.Char(string="Holder Name")
    employee_id = fields.Many2one('hr.employee')

    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         if rec.name:
    #             name = str(rec.name.name) + ' - ' + str(rec.acc_number)
    #         else:
    #             name = str("False") + ' - ' + str(rec.acc_number)
    #         result.append((rec.id, name))
    #     return result
    
    @api.onchange('employee_id')
    def _onchange_employee(self):
        for rec in self:
            if rec.employee_id:
                rec.acc_holder = rec.employee_id.name

class ResBank(models.Model):
    _inherit = "res.bank"

    def name_get(self):
        return [(bank.id, bank.name) for bank in self]