from odoo import api, fields, models
from odoo.exceptions import UserError


class RecurringInvoice(models.Model):
    _name = 'agreement.recurring.invoice'
    _description = 'Recurring Invoice'

    name = fields.Char(string='Recurring Invoice Name', required=True)
    recurring_type = fields.Selection([('daily',"Daily"),('monthly',"Monthly"),('yearly',"Yearly")], default="monthly", string='Payment Type')
    recurring_duration = fields.Integer(string='Recurring Duration', required=True)
    