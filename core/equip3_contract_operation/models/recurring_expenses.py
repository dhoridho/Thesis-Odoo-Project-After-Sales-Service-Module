from odoo import api, fields, models
from odoo.exceptions import UserError


class RecurringExpenses(models.Model):
    _name = 'agreement.recurring.expenses'
    _description = 'Recurring Expenses'

    name = fields.Char(string='Recurring Expenses Name', required=True)
    recurring_type = fields.Selection([('day',"Day"),('week',"Week"),('month',"Month"),('year',"Year")], default="day")
    day = fields.Integer(string='#Day', default=1)
    week = fields.Integer(string='#Week', default=1)
    month = fields.Integer(string='#Month', default=1)
    year = fields.Integer(string='#Year', default=1)
    recurring_duration = fields.Integer(string='Recurring Duration', required=True)
    
    
    @api.model
    def create(self, vals):
        res = super(RecurringExpenses,self).create(vals)
        if res:
            if res.recurring_type == 'day':
                res.year = False
                if res.month <= 0:
                    raise UserError(("Please enter valid day in number...!"))
            if res.recurring_type == 'week':
                res.year = False
                if res.month <= 0:
                    raise UserError(("Please enter valid week in number...!"))
            if res.recurring_type == 'month':
                res.year = False
                if res.month <= 0:
                    raise UserError(("Please enter valid month in number...!"))
            if res.recurring_type == 'year':
                res.month = False
                if res.year <= 0:
                    raise UserError(("Please enter valid year in number...!"))
        return res
