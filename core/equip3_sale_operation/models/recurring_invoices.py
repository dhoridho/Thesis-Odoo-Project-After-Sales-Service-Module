from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class RecurringInvoices(models.Model):
    _name = 'recurring.invoices'
    _description = "Recurring Invoice"

    sale_id = fields.Many2one('sale.order', string="Sale Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    company_id = fields.Many2one(related='sale_id.company_id', string="Company", store=True)
    sequence = fields.Integer("No")
    is_dp = fields.Boolean("Is DP")
    name = fields.Char("Invoice Number", related='invoice_id.display_name', store=True)
    invoice_date = fields.Date("Invoice Date")
    total = fields.Monetary(string="Total")
    currency_id = fields.Many2one('res.currency', related='sale_id.currency_id', store=True)
