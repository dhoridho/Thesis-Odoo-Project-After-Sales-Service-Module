from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


class AssetBudgetAccouting(models.Model):
    _name = 'asset.budget.accounting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Asset Budget'
    _rec_name = 'name'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    name = fields.Char(string='Asset Budget Name', required=True, index=True)
    is_parent_budget = fields.Boolean(string='Is Parent Budget', default=False)
    parent_id = fields.Many2one('asset.budget.accounting', string='Parent Budget', domain="[('is_parent_budget', '=', True)]")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", required=True)
    date_from = fields.Date('Start Date', required=True, tracking=True)
    date_to = fields.Date('End Date', required=True, tracking=True)
    asset_budget_line_ids = fields.One2many('asset.budget.accounting.line', 'asset_budget_id', string='Asset Budget Line')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    amount_planned = fields.Monetary('Planned Amount', compute='_compute_amount_planned')
    amount_used = fields.Monetary('Used Amount', compute='_compute_amount_used')
    amount_remaining = fields.Monetary('Remaining Amount', compute='_compute_amount_remaining')
    amount_remaining_check = fields.Monetary('Remaining Amount')
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=_default_branch)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('confirm', 'Confirmed'),
        ('approved', 'Approved'),
        ('validate', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
    ], string='Status', default='draft', readonly=True, copy=False, index=True, track_visibility='onchange')
    amount_budget = fields.Monetary('Budget Amount', compute='_compute_amount_budget')


    @api.constrains('date_from', 'date_to', 'asset_budget_line_ids', 'account_tag_ids')
    def _check_duplicate_asset_budget(self):
        for budget in self:
            existing_budgets = self.search([
                '|',
                '&', ('date_from', '<', budget.date_from), ('date_to', '>', budget.date_from),
                '&', ('date_from', '<=', budget.date_to), ('date_to', '>=', budget.date_to),
                ('account_tag_ids', 'in', budget.account_tag_ids.ids),
                ('asset_budget_line_ids.asset_budgetary_position_id', 'in', budget.asset_budget_line_ids.mapped('asset_budgetary_position_id').ids),
                ('state', 'in', ['confirm', 'validate']),
                ('id', '!=', budget.id)
            ])
            if existing_budgets:
                raise ValidationError(_('cannot create asset budget with similar parameter (product, period, and analytic group))'))


    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:  
            raise ValidationError(_('The selected period is invalid. The start date must be anterior to the end date.'))

    @api.depends('asset_budget_line_ids.planned_amount')
    def _compute_amount_planned(self):
        for budget in self:
            budget.amount_planned = sum(budget.asset_budget_line_ids.mapped('planned_amount'))

    @api.depends('asset_budget_line_ids.used_amount')
    def _compute_amount_used(self):
        for budget in self:
            budget.amount_used = sum(budget.asset_budget_line_ids.mapped('used_amount'))

    @api.depends('asset_budget_line_ids.remaining_amount')
    def _compute_amount_remaining(self):
        for budget in self:
            budget.amount_remaining = sum(budget.asset_budget_line_ids.mapped('remaining_amount'))
            budget.amount_remaining_check = sum(budget.asset_budget_line_ids.mapped('remaining_amount'))

    @api.depends('asset_budget_line_ids.budget_amount')
    def _compute_amount_budget(self):
        for budget in self:
            budget.amount_budget = sum(budget.asset_budget_line_ids.mapped('budget_amount'))

    def action_reject(self):
        self.write({'state': 'reject'})

    def action_cancel(self):
        if self.amount_remaining < self.amount_planned:
            raise ValidationError(_('You cannot cancel a budget that has been used.'))
        else:
            self.write({'state': 'cancel'})

    def request_approval(self):
        self.write({'state': 'to_approve'})

    def action_approve(self):
        self.write({'state': 'confirm'})

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_validate(self):
        self.write({'state': 'validate'})

    def action_done(self):
        self.write({'state': 'done'})

    def cron_move_to_done(self):
        today = date.today()
        # self.env['asset.budget.accounting'].search([('date_to', '<', today), ('state', 'in', ['confirm', 'validate'])]).write({'state': 'done'})
        budgets = self.search([('date_to', '<', today), ('state', 'in', ['confirm', 'validate'])])
        for budget in budgets:
            budget.write({'state': 'done'})

class AssetBudgetLine(models.Model):
    _name = 'asset.budget.accounting.line'
    _description = 'Asset Budget Line'
    _rec_name = 'asset_budgetary_position_id'


    asset_budget_id = fields.Many2one('asset.budget.accounting', string='Asset Budget', required=True, ondelete='cascade', index=True, copy=False)
    asset_budgetary_position_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    parent_analytic_account_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", required=True)
    # analytic_group_id = fields.Many2one('account.analytic.group', string='Analytic Group', related='account_tag_ids.group_id', readonly=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', related='asset_budget_id.company_id', string='Company',)
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    carry_over_amount = fields.Monetary('Carry Over Amount', readonly=True)
    transfer_amount = fields.Monetary('Transfer Amount', readonly=True)
    change_request_amount = fields.Monetary('Change Request Amount', readonly=True)
    budget_amount = fields.Monetary('Budget Amount', compute='_compute_budget_amount')
    used_amount = fields.Monetary('Used Amount', compute='_compute_used_amount')
    used_amount_check = fields.Monetary('Used Amount')
    remaining_amount = fields.Monetary('Remaining Amount', compute='_compute_remaining_amount')
    remaining_amount_check = fields.Monetary('Remaining Amount')
    theoritical_amount = fields.Monetary('Theoritical Amount', readonly=True)
    achieved_amount = fields.Monetary('Achieved Amount', compute='_compute_achieved_amount')


    

    @api.onchange('planned_amount')
    def _onchange_planned_amount(self):
        if self.asset_budget_id.parent_id:
            if self.planned_amount > self.asset_budget_id.parent_id.amount_remaining:
                raise ValidationError(_('The planned amount cannot be greater than the remaining amount of the budget.'))
            if self.planned_amount < 0:
                raise ValidationError(_('The planned amount cannot be negative.'))

    def action_open_asset_budget_entries(self):
        # if self.account_tag_ids:
            # if there is an analytic account, then the analytic items are loaded
            # action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            # action['domain'] = [('account_id', '=', self.account_tag_ids.ids),
            #                     ('date', '>=', self.date_from),
            #                     ('date', '<=', self.date_to)
            #                     ]
            # if self.asset_budgetary_position_id:
            #     action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        move_ids = []
        domain_mro = [('task_check_list_ids.equipment_id', '=', self.asset_budgetary_position_id.id),
                            ('analytic_group_id', 'in', self.account_tag_ids.ids),
                            ('date_start', '>=', self.date_from),
                            ('date_stop', '<=', self.date_to)]
        mro_obj = self.env['maintenance.repair.order'].search(domain_mro)
        for asset_mro in mro_obj:
            move_ids += self.env['account.move'].search([('repair_order_id', '=', asset_mro.id)]).ids

        domain_mwo = [('task_check_list_ids.equipment_id', '=', self.asset_budgetary_position_id.id),
                        ('analytic_group_id', 'in', self.account_tag_ids.ids),
                        ('startdate', '>=', self.date_from),
                        ('enddate', '<=', self.date_to)]
        mwo_obj = self.env['maintenance.work.order'].search(domain_mwo)
        for asset_mwo in mwo_obj:
            move_ids += self.env['account.move'].search([('work_order_id', '=', asset_mwo.id)]).ids

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        action['domain'] = [('id', 'in', move_ids)]


        # else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            # action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            # action['domain'] = [('account_id', 'in',
            #                      self.asset_budgetary_position_id.account_ids.ids),
            #                     ('analytic_tag_ids', 'in', self.account_tag_ids.ids),
            #                     ('date', '>=', self.date_from),
            #                     ('date', '<=', self.date_to)
            #                     ]
        return action
    
    @api.depends('planned_amount', 'carry_over_amount', 'transfer_amount', 'change_request_amount')
    def _compute_budget_amount(self):
        for line in self:
            line.budget_amount = line.planned_amount + line.carry_over_amount + line.transfer_amount + line.change_request_amount

    
    @api.depends('asset_budget_id', 'asset_budgetary_position_id', 'account_tag_ids', 'date_from', 'date_to')
    def _compute_used_amount(self):
        for line in self:
            line.used_amount = 0.0
            if line.asset_budget_id.state != 'done':
                if line.asset_budget_id.is_parent_budget:
                    child_budgets = self.env['asset.budget.accounting'].search([('parent_id', '=', line.asset_budget_id.id)])
                    for child_budget in child_budgets:
                        for child_line in child_budget.asset_budget_line_ids:
                            if child_line.asset_budgetary_position_id == line.asset_budgetary_position_id:
                                line.used_amount += child_line.used_amount
                else:
                    acc_ids = line.account_tag_ids.ids
                    date_from = line.date_from
                    date_to = line.date_to

                    domain_mro = [('task_check_list_ids.equipment_id', '=', line.asset_budgetary_position_id.id),
                                ('analytic_group_id', 'in', acc_ids),
                                ('date_start', '>=', date_from),
                                ('date_stop', '<=', date_to),
                                ('state_id', '=', 'done')]
                    mro_obj = self.env['maintenance.repair.order'].search(domain_mro)
                    for asset_mro in mro_obj:
                        # used_amount = asset_mro.maintenance_materials_list_ids.mapped('price_subtotal')
                        used_amount = asset_mro.amount_total
                        # line.used_amount += sum(used_amount)
                        line.used_amount += used_amount
                        line.used_amount_check = line.used_amount

                    domain_mwo = [('task_check_list_ids.equipment_id', '=', line.asset_budgetary_position_id.id),
                                ('analytic_group_id', 'in', acc_ids),
                                ('startdate', '>=', date_from),
                                ('enddate', '<=', date_to),
                                ('state_id', '=', 'done')]
                    mwo_obj = self.env['maintenance.work.order'].search(domain_mwo)
                    for asset_mwo in mwo_obj:
                        # used_amount = asset_mwo.maintenance_materials_list_ids.mapped('price_subtotal')
                        used_amount = asset_mwo.amount_total
                        # line.used_amount += sum(used_amount)
                        line.used_amount += used_amount
                        line.used_amount_check = line.used_amount
            else:
                line.used_amount = line.used_amount_check
                if line.used_amount < 0:
                    line.used_amount = line.used_amount * -1

    # @api.depends('planned_amount', 'carry_over_amount', 'transfer_amount', 'change_request_amount', 'used_amount')
    @api.depends('budget_amount', 'used_amount')
    def _compute_remaining_amount(self):
        for line in self:
            # line.remaining_amount = (line.planned_amount + line.carry_over_amount + line.transfer_amount + line.change_request_amount) - line.used_amount
            line.remaining_amount = line.budget_amount - line.used_amount
            line.remaining_amount_check = line.remaining_amount
            # if line.remaining_amount < 0:
            #     raise ValidationError(_('The remaining amount cannot be negative.'))
            
    @api.depends('used_amount', 'theoritical_amount')
    def _compute_achieved_amount(self): 
        for line in self:
            if line.theoritical_amount != 0:
                line.achieved_amount = line.used_amount / line.theoritical_amount
            else:
                line.achieved_amount = 0 


    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if self.date_from < self.asset_budget_id.date_from or self.date_from > self.asset_budget_id.date_to:
            raise ValidationError(_('Start date” and “end date” of the Asset Budget Line should be included in the Period of the budget.'))
        
        if self.date_to < self.asset_budget_id.date_from or self.date_to > self.asset_budget_id.date_to:
            raise ValidationError(_('Start date” and “end date” of the Asset Budget Line should be included in the Period of the budget.'))