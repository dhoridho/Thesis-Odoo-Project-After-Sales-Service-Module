from odoo import tools, api, fields, models, _
from odoo.exceptions import ValidationError


class AccountWorkingCapital(models.Model):
    _name = 'account.working.capital'
    _description = "Working Capital"
    _inherit = ['mail.thread']


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id','in',self.env.branches.ids), ('company_id','=',self.env.company.id)]

    @api.model
    def _domain_journal(self):
        return [('type','in',['bank','cash']), ('company_id','=',self.env.company.id)]

    name = fields.Char(string='Name', default='/', tracking=True, readonly=True)
    plafond_amount = fields.Monetary(string='Plafond', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validate', 'Validate')
        ], 'Status', readonly=True, copy=False, tracking=True, default='draft')
    available_plafond_amount = fields.Monetary(string='Available Plafond', required=True)
    monthly_interest_rate = fields.Float(string='Monthly Interest Rate', required=True)
    bank_id = fields.Many2one('res.bank', string='Bank Partner', required=True)
    daily_interest_rate = fields.Float(string='Daily Interest Rate', readonly=True)
    accounting_date = fields.Date(string='Accounting Date')
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    cut_off_date = fields.Integer('Cut Off Date', default=25, required=True)
    current_active_loan_amount = fields.Monetary(string='Current Active Loan', readonly=True)
    remaining_plafond_amount = fields.Monetary(string='Remaining Plafond', compute='_compute_remaining_plafond_amount')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default=_default_branch, required=True)
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    journal_id = fields.Many2one('account.journal', string="Journal", domain=_domain_journal)
    account_working_capital_line_ids = fields.One2many('account.working.capital.line', 'working_capital_id', string="Item Lines")


    @api.depends('plafond_amount','available_plafond_amount')
    def _compute_remaining_plafond_amount(self):
        for record in self:
            record.remaining_plafond_amount = record.plafond_amount - record.available_plafond_amount

    def action_validate(self):
        for record in self:
            record.write({
                'name': self.env['ir.sequence'].next_by_code('working.capital.seq'),
                'state': 'validate',
            })


class AccountWorkingCapitalLines(models.Model):
    _name = 'account.working.capital.line'
    _description = "Working Capital Line"


    working_capital_id = fields.Many2one('account.working.capital', string="Working Capital")
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    plafond_amount = fields.Monetary(string='Plafond', related='working_capital_id.plafond_amount')
    interest_rate = fields.Float(string='Interest Rate', related='working_capital_id.daily_interest_rate')
    accumulated_interest_amount = fields.Monetary(string='Accumulated Interest', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='working_capital_id.currency_id')

    def action_close(self):
        return True