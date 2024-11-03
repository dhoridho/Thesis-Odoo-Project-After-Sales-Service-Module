from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
from datetime import timedelta


class BudgetCarryOver(models.Model):
    _name = "budget.carry.over"
    _description = "Budget Carry Over"
    _inherit = ['mail.thread']


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)

    name = fields.Char('Budget Name', states={'done': [('readonly', True)]})
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    crossover_budget_id = fields.Many2one('crossovered.budget', string="Budget Reference")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')
        ], 'Status', readonly=True, copy=False, tracking=True, default='draft')
    parent_id = fields.Many2one('crossovered.budget', 'Parent Budget', index=True, ondelete='cascade', domain="[('state', '=', 'validate'), ('is_parent_budget', '=', True)]")
    # branch_id = fields.Many2one('res.branch', readonly=False, default=lambda self: self.env.user.branch_id.id)
    is_parent_budget = fields.Boolean(string="Is Parent Budget", default=False)
    budget_carry_over_line_ids = fields.One2many('budget.carry.over.lines', 'budget_carry_over_id', string="Budget Lines")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date('Start Date', required=True, states={'done': [('readonly', True)]}, default=fields.Date.context_today)
    date_to = fields.Date('End Date', required=True, states={'done': [('readonly', True)]}, default=fields.Date.context_today)
    # branch_id = fields.Many2one('res.branch', readonly=False, default=lambda self: self.env.user.branch_id.id)
    is_use_theoretical_achievement = fields.Boolean(string="Is use Theoritical amount and Achievement", compute="_get_use_theoretical_achievement_config")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups")
    new_crossovered_budget_id = fields.Many2one('crossovered.budget', string="New Budget Reference")


    @api.constrains('crossed_budget_id', 'parent_id')
    def _check_crossed_budget_id(self):
        for record in self:
            if record.crossover_budget_id and record.parent_id:
                child_budgetary_positions = record.crossover_budget_id.crossovered_budget_line.mapped('general_budget_id')
                parent_budgetary_positions = record.parent_id.crossovered_budget_line.mapped('general_budget_id')

                # Check if any of the child budgetary positions are not in the parent budgetary positions
                if not all(position in parent_budgetary_positions for position in child_budgetary_positions):
                    raise ValidationError("The reference budget has different budgetary position with the parent budget.")

    @api.depends('name')
    def _get_use_theoretical_achievement_config(self):
        is_use_theoretical_achievement = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_budget.accounting_budget_use_theoretical_achievement', False)
        self.is_use_theoretical_achievement = is_use_theoretical_achievement
        
    
    @api.depends('branch_id', 'crossover_budget_id')
    def get_account_tag_ids(self):
        if self.branch_id:
            self.account_tag_ids = self.branch_id.analytic_tag_ids

        if self.crossover_budget_id:
            self.account_tag_ids = self.crossover_budget_id.account_tag_ids

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if self.date_from or self.date_to:
            for line in self.budget_carry_over_line_ids:
                if self.date_from:
                    line.date_from = self.date_from
                if self.date_to:
                    line.date_to = self.date_to

    @api.onchange('crossover_budget_id')
    def _onchage_crossover_budget_id_fill(self):
        data = [(5, 0, 0)]
        for record in self:
            
            record.is_parent_budget = record.crossover_budget_id.is_parent_budget
            record.parent_id = record.crossover_budget_id.parent_id
            record.branch_id = record.crossover_budget_id.branch_id or self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id
            record.account_tag_ids = record.crossover_budget_id.account_tag_ids
            # record.date_from = record.crossover_budget_id.date_from
            # record.date_to = record.crossover_budget_id.date_to

            for line in record.crossover_budget_id.crossovered_budget_line:
                data.append((0, 0, {
                    'general_budget_id': line.general_budget_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'paid_date': line.paid_date,
                  # 'planned_amount': line.planned_amount,
                    'carry_over_amount': line.remaining_amount,
                    'remaining_amount': line.remaining_amount,
                    'reserve_amount': line.reserve_amount,
                    'practical_amount': line.practical_budget_amount,
                    # 'theoritical_amount': line.theoritical_amount_2,
                    # 'percentage': line.percentage_2,
                }))
            record.budget_carry_over_line_ids = data

    def action_carryover_budget_confirm(self):
        for record in self:
            # line_data = [(0, 0, {
            #     'general_budget_id': line.general_budget_id.id,
            #     'account_tag_ids': line.account_tag_ids.ids,
            #     'date_from': line.date_from,
            #     'date_to': line.date_to,
            #     'paid_date': line.paid_date,
            #     'planned_amount': line.planned_amount,
            #     'reserve_amount': line.reserve_amount,
            #     'practical_budget_amount': line.practical_budget_amount,
            #     'theoritical_amount': line.theoritical_amount,
            #     'percentage': line.percentage,
            #     # 'carry_over_amount': line.carry_over_amount,
            # }) for line in record.budget_carry_over_line_ids]
            vals = {
                'name' : record.name,
                'is_parent_budget' : record.is_parent_budget,
                'parent_id' : record.parent_id.id,
                'account_tag_ids' : record.account_tag_ids.ids,
                'date_from' : record.date_from,
                'date_to' : record.date_to,
                'company_id': record.company_id.id,
                'branch_id': record.branch_id.id,
                # 'crossovered_budget_line': line_data,
            }
            crossovered_budget = self.env['crossovered.budget'].create(vals)

            record.write({'state': 'confirm', 'new_crossovered_budget_id': crossovered_budget.id})

            for line in record.budget_carry_over_line_ids:
                if line.carry_over_amount <= 0:
                    raise ValidationError("Carry over amount must be greater than 0!")
                if line.carry_over_amount > line.remaining_amount:
                    raise ValidationError("Carry over amount cannot bigger than remaining amount %s" % record.crossover_budget_id.name)
                if line.final_planned_amount <= 0:
                    raise ValidationError("Final budget amount must be greater than 0!")
                if record.parent_id:
                    crossovered_budget_lines = self.env['crossovered.budget.lines'].search([
                        ('general_budget_id', '=', line.general_budget_id.id),
                        ('crossovered_budget_id', '=', record.parent_id.id)
                    ])
                    for budget_line in crossovered_budget_lines:
                        if line.final_planned_amount > budget_line.available_to_child_amount:
                            raise ValidationError("You cannot allocate more than the parent budget amount.")

                vals = {
                    'general_budget_id': line.general_budget_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'paid_date': line.paid_date,
                    'planned_amount': line.planned_amount,
                    'reserve_amount': line.reserve_amount,
                    'practical_budget_amount': line.practical_budget_amount,
                    'theoritical_amount': line.theoritical_amount,
                    'percentage': line.percentage,
                    'crossovered_budget_id': crossovered_budget.id
                    # 'crossovered_budget_line': line_data,
                }
                crossovered_budget_line = self.env['crossovered.budget.lines'].create(vals)
                line.write({'new_crossovered_budget_line_id': crossovered_budget_line.id})


    @api.onchange('is_parent_budget') 
    def _onchange_is_parent_budget(self):
        for budget in self:
            if budget.is_parent_budget:
                budget.account_tag_ids = False
                for line in budget.budget_carry_over_line_ids:
                    line.account_tag_ids = False

class BudgetCarryOverLines(models.Model):
    _name = "budget.carry.over.lines"
    _description = "Budget Carry Over Lines"

    budget_carry_over_id = fields.Many2one('budget.carry.over', string='Carry Over Budget')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    paid_date = fields.Date('Paid Date')
    parent_analytic_account_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position')
    reserve_amount = fields.Monetary('Reserve Amount', compute='_get_reserve_amount', store=False)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    # account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_cb_rel', 'budget_id', 'tag_id', related="budget_carry_over_id.account_tag_ids", string="Analytic Group")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", compute='get_account_tag_ids', 
        inverse='_set_account_tag_ids', 
        store=True)
    
    filtered_budget_line = fields.Many2many('account.budget.post', store=False, compute='_get_budget_line')
    company_id = fields.Many2one(related='budget_carry_over_id.company_id', comodel_name='res.company',
        string='Company', store=True, readonly=True)
    practical_amount = fields.Monetary(
        string='Used Amount', help="Amount really earned/spent.", default=0, readonly=True)
    theoritical_amount = fields.Monetary(
        compute='_compute_theoritical_amount', string='Theoretical Amount',
        help="Amount you are supposed to have earned/spent at this date.")
    planned_amount = fields.Monetary(
        'Planned Amount',
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    practical_budget_amount = fields.Monetary(
        compute='_compute_budget_practical_amount', store=False, string='Used Amount', help="Amount really earned/spent.")
    percentage = fields.Float(
        compute='_compute_percentage', string='Achievement',
        help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    is_above_budget = fields.Boolean(compute='_is_above_budget')
    carry_over_amount = fields.Monetary('Carry Over Amount')
    remaining_amount = fields.Monetary('Remaining Amount')
    final_planned_amount = fields.Monetary('Final Budget Amount', compute='_compute_final_planned_amount', store=True)
    crossover_budget_id = fields.Many2one('crossovered.budget', string="Budget Reference", related="budget_carry_over_id.crossover_budget_id")
    budget_carry_over_name = fields.Char('Budget Name', related="budget_carry_over_id.name")
    account_tag_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_account_tag_ids_domain')
    new_crossovered_budget_id = fields.Many2one('crossovered.budget', string="New Budget Reference", related="budget_carry_over_id.new_crossovered_budget_id")
    new_crossovered_budget_id_state = fields.Selection(related='new_crossovered_budget_id.state')
    new_crossovered_budget_line_id = fields.Many2one('crossovered.budget.lines', string="New Budget Reference Line")
    new_crossovered_budget_line_account_tag_ids = fields.Many2many(related='new_crossovered_budget_line_id.account_tag_ids')
    new_crossovered_budget_line_date_from = fields.Date(related='new_crossovered_budget_line_id.date_from')
    new_crossovered_budget_line_date_to = fields.Date(related='new_crossovered_budget_line_id.date_to')
    # general_budget_id_domain = fields.Char(string='Budgetary Position Domain', compute='_compute_budget_domain')


    # @api.depends('budget_carry_over_id.crossover_budget_id')
    # def _compute_budget_domain(self):
    #     budget_ids = []
    #     for line in self.budget_carry_over_id.crossover_budget_id.crossovered_budget_line:
    #         budget_ids.append(line.general_budget_id.id)

    #     self.general_budget_id_domain = json.dumps([('id','in',budget_ids)])

    @api.depends('budget_carry_over_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        if self.budget_carry_over_id:
            self.account_tag_ids_domain = json.dumps([('id','in',self.budget_carry_over_id.account_tag_ids.ids)])

    @api.depends('budget_carry_over_id.account_tag_ids')
    def get_account_tag_ids(self):
        for record in self:
            # Directly copying the account_tag_ids from budget_carry_over_id to this model's account_tag_ids
            record.account_tag_ids = record.budget_carry_over_id.account_tag_ids

    def _set_account_tag_ids(self):
        for record in self:
            # Handle user updates to account_tag_ids here
            # This method is needed to allow edits on the computed field from the UI
            # You might want to implement logic that syncs changes back to budget_carry_over_id or handles them appropriately
            pass


    @api.depends('budget_carry_over_id', 'budget_carry_over_id.parent_id')
    def _get_budget_line(self):
        for record in self:
            if record.budget_carry_over_id.parent_id:
                line_ids = record.budget_carry_over_id.parent_id.crossovered_budget_line.mapped('general_budget_id')
                record.filtered_budget_line = [(6, 0, line_ids.ids)]
            else:
                line_ids = self.env['account.budget.post'].search([])
                record.filtered_budget_line = [(6, 0, line_ids.ids)]

    @api.depends('planned_amount', 'carry_over_amount')
    def _compute_final_planned_amount(self):
        for record in self:
            record.final_planned_amount = record.planned_amount + record.carry_over_amount

    def _get_reserve_amount(self):
        for record in self:
            parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.budget_carry_over_id.id)])
            crossovered_budget_line = parent_ids.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == record.general_budget_id.id)
            record.reserve_amount = sum(crossovered_budget_line.mapped('planned_amount'))

    @api.onchange('theoritical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                crossovered_budget_line = self.env['crossovered.budget.lines'].search([
                    ('general_budget_id', '=', line.general_budget_id.id),
                    ('crossovered_budget_id', '=', line.budget_carry_over_id.crossover_budget_id.id),                     
                ], limit=1)
                line.percentage = (crossovered_budget_line.reserve_amount_2 + crossovered_budget_line.pr_reserved_amount + crossovered_budget_line.practical_budget_amount + crossovered_budget_line.purchased_amount) / line.theoritical_amount
            else:
                line.percentage = 0.00

    def _compute_budget_practical_amount(self):
        for line in self:
            if line.budget_carry_over_id.is_parent_budget:
                parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', line.budget_carry_over_id.id)])
                crossovered_budget_line = parent_ids.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.general_budget_id.id)
                line.practical_budget_amount = sum(crossovered_budget_line.mapped('practical_budget_amount'))
            else:
                acc_ids = line.general_budget_id.account_ids.ids
                date_to = line.date_to
                date_from = line.date_from
                if line.analytic_account_id.id:
                    analytic_line_obj = self.env['account.analytic.line']
                    domain = [('account_id', '=', line.analytic_account_id.id),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ]
                    if acc_ids:
                        domain += [('general_account_id', 'in', acc_ids)]

                    where_query = analytic_line_obj._where_calc(domain)
                    analytic_line_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

                else:
                    aml_obj = self.env['account.move.line']
                    domain = [('account_id', 'in',
                               line.general_budget_id.account_ids.ids),
                              ('date', '>=', date_from),
                              ('date', '<=', date_to),
                              ('move_id.is_from_receiving_note','=',False),
                              ]
                    where_query = aml_obj._where_calc(domain)
                    aml_obj._apply_ir_rules(where_query, 'read')
                    from_clause, where_clause, where_clause_params = where_query.get_sql()
                    select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

                self.env.cr.execute(select, where_clause_params)
                line.practical_budget_amount = self.env.cr.fetchone()[0] or 0.0

    @api.onchange('final_planned_amount')
    def _compute_theoritical_amount(self):
        # beware: 'today' variable is mocked in the python tests and thus, its implementation matter
        today = fields.Date.today()
        for line in self:
            if line.paid_date:
                if today <= line.paid_date:
                    theo_amt = 0.00
                else:
                    theo_amt = line.final_planned_amount
            else:
                if line.date_to and line.date_from:
                    line_timedelta = line.date_to - (line.date_from - timedelta(days=1))
                    elapsed_timedelta = today - (line.date_from - timedelta(days=1))

                    if elapsed_timedelta.days < 0:
                        # If the budget line has not started yet, theoretical amount should be zero
                        theo_amt = 0.00
                    elif line_timedelta.days > 0 and today < line.date_to:
                        # If today is between the budget line date_from and date_to
                        theo_amt = (elapsed_timedelta / line_timedelta) * line.final_planned_amount
                    else:
                        theo_amt = line.final_planned_amount
                else:
                    theo_amt = line.final_planned_amount
            line.theoritical_amount = theo_amt

    def action_open_carry_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            action['domain'] = [('account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.general_budget_id.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action

    def _is_above_budget(self):
        for line in self:
            if line.theoritical_amount >= 0:
                line.is_above_budget = line.practical_amount > line.theoritical_amount
            else:
                line.is_above_budget = line.practical_amount < line.theoritical_amount