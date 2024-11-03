from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class RecurAccountPayment(models.Model):
    _inherit = 'account.payment'

    is_prepayment = fields.Boolean(string='Prepayment')
    prepayment_journal_id = fields.Many2one(comodel_name='account.journal')
    start_date = fields.Date(string='Start Date', default=fields.Datetime.now)
    end_date = fields.Date(string='End Date', compute='_onchange_stop_recurring_interval')
    recurring_interval = fields.Integer(string='Interval')
    recurring_interval_unit = fields.Selection([('days', 'Days'), ('weeks','Weeks'), ('months','Months'), ('years','Years')], default='days')
    stop_recurring_interval = fields.Integer(string='Stop After')
    stop_recurring_interval_unit = fields.Selection([('days', 'Days'), ('weeks','Weeks'), ('months','Months'), ('years','Years')])
    revenue_account = fields.Many2one(comodel_name='account.account')

    @api.onchange('partner_type')
    def _onchange_domain(self):
        self.ensure_one()
        res={}
        if self.partner_type == "customer":
            domain_line = "[('user_type_id.name', 'in', ['Income','Other Income'])]"
        else:
            domain_line = "[('user_type_id.name', 'in', ['Expenses','Depreciation','Cost of Revenue'])]"
        res['domain'] = {'revenue_account' : domain_line}
        return res

    @api.depends('stop_recurring_interval',
                  'recurring_interval_unit', 'start_date')
    def _onchange_stop_recurring_interval(self):
        for rec in self:
            print(rec.partner_type)
            rec.stop_recurring_interval_unit = rec.recurring_interval_unit
        if self and self.start_date:
            if self.stop_recurring_interval > 0:
                end_date = False
                st_date = fields.Date.from_string(self.start_date)
                if self.recurring_interval_unit == 'days':
                    end_date = st_date + \
                        relativedelta(days=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'weeks':
                    end_date = st_date + \
                        relativedelta(weeks=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'months':
                    end_date = st_date + \
                        relativedelta(months=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'years':
                    end_date = st_date + \
                        relativedelta(years=self.stop_recurring_interval - 1)

                if end_date:
                    self.end_date = end_date
            else:
                self.end_date = False