from odoo import api, fields, models, _


class ExpenseFlow(models.TransientModel):
    _name = 'hr.expense.flow'

    name = fields.Char('Name', default='Expense Flow')

    def action_none(self):
        pass
