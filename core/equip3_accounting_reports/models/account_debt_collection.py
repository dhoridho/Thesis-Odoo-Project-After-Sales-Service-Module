from odoo import fields, models, _ , api
from odoo.exceptions import ValidationError, UserError
from odoo.tools import date_utils
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from calendar import weekday



class AccountDebtCollectionLine(models.Model):
    _inherit = 'account.debt.collection.line'

    user_id = fields.Many2one('res.users', related="debt_collection_id.person_in_charge")
    partner_id = fields.Many2one('res.partner', related="debt_collection_id.partner_id", store=True)
    deadline_date = fields.Date(related="debt_collection_id.deadline_date", store=True)
    invoice_due_date = fields.Date(related="invoice_id.invoice_date_due", store=True)
    total_due_date = fields.Integer(compute="_compute_total_due_date")
    debt_coll_pic = fields.Many2one('res.users',string="Person in Charge", compute="_compute_debt_coll_pic", store=True)
    invoice_week_number = fields.Integer(compute="_compute_invoice_week_number", store=True)
    invoice_week_start = fields.Date(compute="_compute_invoice_week_start", store=True)


    @api.depends('invoice_date')
    def _compute_invoice_week_start(self):
        for rec in self:
            if rec.invoice_date:
                rec.invoice_week_start = date_utils.start_of(rec.invoice_date, 'week')

    @api.depends('invoice_date')
    def _compute_invoice_week_number(self):
        for rec in self:
            if rec.invoice_date:
                rec.invoice_week_number = rec.invoice_date.isocalendar()[1]

    @api.depends('partner_id')
    def _compute_debt_coll_pic(self):
        for rec in self:
            debt_pic = self.env['account.debt.collection'].search([('id', '=', rec.debt_collection_id.id)])
            rec.debt_coll_pic = debt_pic.person_in_charge.id

    @api.depends('invoice_due_date')
    def _compute_total_due_date(self):
        for rec in self:
            rec.total_due_date = (rec.invoice_due_date - rec.invoice_id.invoice_date)


