from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------

class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"
    _parent_name = "parent_id"
    _rec_name = 'complete_name'
    _order = 'complete_name'

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
        tracking=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)

    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    parent_id = fields.Many2one('crossovered.budget', 'Parent Budget', index=True, ondelete='cascade')
    # branch_id = fields.Many2one('res.branch', readonly=False, default=lambda self: self.env.user.branch_id.id)
    
    is_parent_budget = fields.Boolean(string="Is Parent Budget", default=False)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", required=True)
    date_today = fields.Date(string='Today Date', compute="_compute_practical_budget_total", store=True, default=fields.Date.today())
    is_use_theoretical_achievement = fields.Boolean(string="Is use Theoritical amount and Achievement", compute="_get_use_theoretical_achievement_config")
    currency_company_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    # amount_planned = fields.Float(string='Planned Amount', compute='_compute_amount_planned')
    amount_planned = fields.Monetary(string='Planned Amount', compute='_compute_amount_planned')
    # amount_practical = fields.Float(string='Used Amount', compute='_compute_amount_practical')
    amount_practical = fields.Monetary(string='Realized Amount', compute='_compute_amount_practical', currency_field='currency_company_id')
    amount_practical_temp = fields.Float(string='Realized Amount Temp', compute='_compute_amount_practical', store=True)
    # amount_remaining = fields.Float(string='Remaining Amount', compute='_compute_amount_remaining')
    # amount_remaining_temp = fields.Float(string='Remaining Amount Temp', compute='_compute_amount_remaining', store=True)
    # amount_remaining = fields.Float(string='Remaining Amount', compute='_compute_amount_practical')
    amount_remaining = fields.Monetary(string='Remaining Amount', compute='_compute_amount_practical', currency_field='currency_company_id', store=True)
    amount_remaining_temp = fields.Float(string='Remaining Amount Temp', compute='_compute_amount_practical', store=True)
    child_budget_ids = fields.One2many('crossovered.budget', 'parent_id', string='Child Budgets')
    transfer_amount = fields.Monetary(string='Transfer Amount', compute='_compute_transfer_amount')
    child_source_budget_transfer_line_ids = fields.One2many('crossovered.budget.transfer.line', 'source_budget_id', string='Child Source Budgets')
    child_destination_budget_transfer_line_ids = fields.One2many('crossovered.budget.transfer.line', 'destination_budget_id', string='Child Destination Budgets')
    child_budget_carry_over_line_ids = fields.One2many('budget.carry.over.lines', 'new_crossovered_budget_id', string='Child Budget Carry Over Lines')
    child_budget_change_req_line_ids = fields.One2many('budget.change.req.line', 'budget_std_id', string='Child Budget Change Request Lines')
    budget_amount = fields.Monetary(string='Budget Amount', compute='_compute_budget_amount')
    child_budget_line_ids = fields.One2many('crossovered.budget.lines', 'parent_id', string='Child Budgets Lines')
    pettycash_voucher_line_ids = fields.One2many('account.pettycash.voucher.wizard.line', 'crossovered_budget_id', string='Pettycash Voucher Lines', domain=[('state','!=','draft')])
    account_voucher_line_ids = fields.One2many('account.voucher.line', 'crossovered_budget_id', string='Account Voucher Lines', domain=[('state','!=','draft')])
    account_move_line_ids = fields.One2many('account.move.line', 'crossovered_budget_id', string='Account Move Lines', domain=[('parent_state','!=','draft')])
    vendor_deposit_ids = fields.One2many('vendor.deposit', 'crossovered_budget_id', string='Vendor Deposit', domain=[('state','!=','draft')])
    reserve_amount_2 = fields.Monetary(string='Account Reserved', compute='_compute_budget_amount')
    child_budget_carry_out_line_ids = fields.One2many('budget.carry.over.lines', 'crossover_budget_id', string='Child Budget Carry Out Lines')
    child_budget_purchase_line_ids = fields.One2many('budget.purchase.lines', 'parent_id', string='Child Purchase Budget Lines')
    total_purchased_amount = fields.Monetary(string='Purchased Amount', compute='_compute_amount_practical', currency_field='currency_company_id')
    total_pr_reserved_amount = fields.Monetary(string='PR Reserved', compute='_compute_amount_practical', currency_field='currency_company_id')


    @api.constrains('date_from', 'date_to', 'account_tag_ids', 'crossovered_budget_line.general_budget_id')
    def _check_duplicate_budget(self):
        for record in self:
        #     existing_budget_count = 0
            existing_budget_ids = self.env['crossovered.budget'].browse([])
            if self.is_parent_budget and not self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from), 
                    ('crossovered_budget_line.general_budget_id', 'in', record.crossovered_budget_line.mapped('general_budget_id').ids), # Including exact match
                    ('id', '!=', record.id),
                    ('state', '=', 'validate')
                ])
            elif self.is_parent_budget and self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    ('crossovered_budget_line.general_budget_id', 'in', record.crossovered_budget_line.mapped('general_budget_id').ids),
                    ('id', '!=', record.id),
                    ('parent_id', '=', record.parent_id.id),
                    ('state', '=', 'validate'),
                    ('is_parent_budget', '=', True),  # Ensure we're only considering parent budgets
                ])
            elif not self.is_parent_budget and self.parent_id:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    ('account_tag_ids', 'in', record.account_tag_ids.ids),
                    ('crossovered_budget_line.general_budget_id', 'in', record.crossovered_budget_line.mapped('general_budget_id').ids),
                    ('id', '!=', record.id),
                    ('state', '=', 'validate'),
                    ('parent_id', '=', record.parent_id.id),
                    ('is_parent_budget','=',False),
                ])
            else:
                existing_budget_ids = self.env['crossovered.budget'].search([
                    '|',
                    '&', ('date_from', '<', record.date_to), ('date_to', '>', record.date_from),  # Overlapping condition
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),  # Including exact match
                    '|', ('account_tag_ids', 'in', record.account_tag_ids.ids),
                    ('account_tag_ids', '=', False),
                    ('crossovered_budget_line.general_budget_id', 'in', record.crossovered_budget_line.mapped('general_budget_id').ids),
                    ('id', '!=', record.id),
                    ('state', '=', 'validate'),
                    ('is_parent_budget','=',False),
                ])
                # query = """
                #     SELECT id FROM crossovered_budget
                #     WHERE (
                #         (date_from < %s AND date_to > %s) OR
                #         (date_from <= %s AND date_to >= %s)
                #     )
                #     AND account_tag_ids = ANY(%s)
                #     AND crossovered_budget_line.general_budget_id = ANY(
                #         SELECT general_budget_id FROM crossovered_budget_line WHERE id IN %s
                #     )
                #     AND id != %s
                #     AND state IN ('draft', 'validate', 'confirm')
                #     AND parent_id = %s
                # """
                # params = [
                #     record.date_to, record.date_from,  # Overlapping and exact match conditions
                #     record.date_to, record.date_from,
                #     tuple(record.account_tag_ids.ids),  # Account tag IDs
                #     tuple(record.crossovered_budget_line.mapped('general_budget_id').ids),  # General budget IDs
                #     record.id,  # Exclude current record
                #     record.parent_id.id if record.parent_id else None,  # Parent ID or None
                # ]
                # self._cr.execute(query, params)
            if existing_budget_ids and not self.is_parent_budget:
                conflicting_budget_names = ', '.join(existing_budget_ids.mapped('name'))
                raise ValidationError(_('You cannot create budget, because it already exists or inside period of budget with names: %s.') % conflicting_budget_names)
                
            if record.parent_id:
                if record.date_from < record.parent_id.date_from or record.date_to > record.parent_id.date_to:
                    raise ValidationError(_('The date is out of the Parent Budget period.'))

            if record.date_to < record.date_from:
                raise ValidationError(_('End date cannot before the start date.'))

    def action_budget_undone(self):
        self.write({'state': 'validate'})

    def action_confirm_dialog(self):
        return {
            'name': _('Confirm'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.budget.confirm',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_budget_id': self.id}
        }

    @api.depends('date_today','crossovered_budget_line.practical_temp_budget')
    def _compute_practical_budget_total(self):
        for record in self.search([('state','!=','done')]):
            today = fields.Date.today()
            if record.date_to and today > record.date_to:
                record.update({'state':'done'})

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    # @api.depends('parent_id')
    # def _get_pparent_account_analytic_id(self):
    #     for record in self:
    #         if record.parent_id:
    #             record.parent_analytic_account_id = record.parent_id.parent_analytic_account_id
    #         for line in record.crossovered_budget_line:
    #             line.analytic_account_id = record.parent_analytic_account_id


    def _update_reserve_anmount_on_approved(self):
        if self.parent_id:
            for record in self:
                for line in record.crossovered_budget_line:
                    parent_crossovered_budget_obj = self.env['crossovered.budget.lines'].search(
                        [('crossovered_budget_id.id', '=', record.parent_id.id),
                         ('crossovered_budget_id.state', '=', 'validate'),
                         ('analytic_account_id.id', '=', line.parent_analytic_account_id.id),
                         ('general_budget_id.id', '=', line.general_budget_id.id)])
                    parent_crossovered_budget_obj.write(
                        {'reserve_amount': parent_crossovered_budget_obj.reserve_amount + line.planned_amount})

                    # sum_planned_amount = sum(self.env['crossovered.budget.lines'].search(
                    #     [('crossovered_budget_id.parent_id.id', '=', record.parent_id.id),
                    #      ('crossovered_budget_id.state', '=', 'validate')]).mapped('planned_amount'))
                    # for line in record.crossovered_budget_line:
                    #     line.reserve_amount = sum_planned_amount

    def _update_reserve_anmount_on_cancel(self):
        if self.parent_id:
            for record in self:
                for line in record.crossovered_budget_line:
                    parent_crossovered_budget_obj = self.env['crossovered.budget.lines'].search(
                        [('crossovered_budget_id.id', '=', record.parent_id.id),
                         ('crossovered_budget_id.state', '=', 'validate'),
                         ('analytic_account_id.id', '=', line.parent_analytic_account_id.id),
                         ('general_budget_id.id', '=', line.general_budget_id.id)])
                    parent_crossovered_budget_obj.write(
                        {'reserve_amount': parent_crossovered_budget_obj.reserve_amount - line.planned_amount})

    def action_budget_validate(self):
        res = super(CrossoveredBudget, self).action_budget_validate()
        self._update_reserve_anmount_on_approved()
        return res
    
    def action_budget_cancel(self):
        if self.is_parent_budget:
            child_budgets = self.env['crossovered.budget'].search([
                ('parent_id', '=', self.id),
                ('amount_practical_temp', '>', 0),
                ('state', 'in', ['validate', 'confirm', 'done'])
            ])
            # If there are child budgets, raise a ValidationError
            if child_budgets:
                child_budget_names = ', '.join(child_budgets.mapped('name'))
                raise ValidationError(_('You cannot cancel this parent budget. Please cancel the child budget(s) %s first.') % child_budget_names)
            
            done_child_budgets = self.env['crossovered.budget'].search([
                ('parent_id', '=', self.id),
                ('state', '=', 'done')
            ], limit=1)
            # If there are child budget with done state, raise a ValidationError
            if done_child_budgets:
                raise ValidationError(_('You cannot cancel this parent budget. There is done child budget linked to this budget'))

            for child in self.child_budget_ids:
                child.action_budget_cancel()
        # For both parent (without child budgets in specified states) and non-parent budgets, proceed with cancellation
        res = super(CrossoveredBudget, self).action_budget_cancel()
        self._update_reserve_anmount_on_cancel()
        return res

    def unlink(self):
        for record in self:
            if record.state in ['validate', 'done']:
                raise ValidationError(_('You cannot delete a budget in state \'%s\'.') % (record.state,))
        return super(CrossoveredBudget, self).unlink()

    @api.depends('crossovered_budget_line.planned_amount')
    def _compute_amount_planned(self):
        for record in self:
            record.amount_planned = sum(record.crossovered_budget_line.mapped('planned_amount'))

    @api.depends('crossovered_budget_line.transfer_amount')
    def _compute_transfer_amount(self):
        for record in self:
            record.transfer_amount = sum(record.crossovered_budget_line.mapped('transfer_amount'))

    @api.depends('crossovered_budget_line.budget_amount','crossovered_budget_line.reserve_amount_2')
    def _compute_budget_amount(self):
        for record in self:
            record.budget_amount = sum(record.crossovered_budget_line.mapped('budget_amount'))
            record.reserve_amount_2 = sum(record.crossovered_budget_line.mapped('reserve_amount_2'))
            
            if record.child_budget_line_ids:
                record.reserve_amount_2 = sum(record.child_budget_line_ids.mapped('reserve_amount_2'))

    @api.depends('crossovered_budget_line.practical_budget_amount', 'transfer_amount', 'crossovered_budget_line.remaining_amount', 'crossovered_budget_line.purchased_amount')
    def _compute_amount_practical(self):
        for record in self:
            if record.is_parent_budget and not record.parent_id:
                # line_ids = record.crossovered_budget_line
                # record.amount_practical = sum(line_ids.mapped('practical_budget_amount'))
                used_amount = 0
                remaining_amount = sum(record.crossovered_budget_line.mapped('remaining_amount'))
                total_planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))
                sub_parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.id)])
                for sub_parent_id in sub_parent_ids:
                    # child_ids = self.env['crossovered.budget'].search([('parent_id', '=', sub_parent_id.id)])
                    # for child_id in child_ids:
                    used_amount += sum(sub_parent_id.crossovered_budget_line.mapped('practical_budget_amount'))
                    record.amount_practical_temp = used_amount
                    record.amount_practical = used_amount
                record.amount_practical = used_amount
                record.amount_practical_temp = used_amount
                if used_amount < 0:
                    used_amount = used_amount * -1
                record.amount_remaining = remaining_amount
                record.amount_remaining_temp = remaining_amount
                record.write({'amount_practical': used_amount,
                               'amount_practical_temp': used_amount,
                                 'amount_remaining': remaining_amount,
                                    'amount_remaining_temp': remaining_amount})
                # print ('===record.amount_practical',record.amount_practical)

            elif record.is_parent_budget and record.parent_id:
                child_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.id)])
                total_planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))

                record.amount_practical_temp = sum(child_ids.crossovered_budget_line.mapped('practical_budget_amount'))
                record.amount_practical = sum(child_ids.crossovered_budget_line.mapped('practical_budget_amount'))
                if record.amount_practical < 0:
                    record.amount_practical = record.amount_practical * -1
                record.amount_remaining = sum(record.crossovered_budget_line.mapped('remaining_amount'))
                record.amount_remaining_temp = record.amount_remaining
            else:
                record.amount_practical = sum(record.crossovered_budget_line.mapped('practical_budget_amount'))
                record.amount_practical_temp = sum(record.crossovered_budget_line.mapped('practical_budget_amount'))
                record.amount_remaining = sum(record.crossovered_budget_line.mapped('remaining_amount'))
            record.total_purchased_amount = sum(record.crossovered_budget_line.mapped('purchased_amount'))
            record.total_pr_reserved_amount = sum(record.crossovered_budget_line.mapped('pr_reserved_amount'))
            
            if record.child_budget_line_ids:
                for child in record.child_budget_line_ids:
                    child._get_child_purchase_amount()
                record.total_purchased_amount = sum(record.child_budget_line_ids.mapped('purchased_amount'))
                record.total_pr_reserved_amount = sum(record.child_budget_line_ids.mapped('pr_reserved_amount'))

    # @api.depends('crossovered_budget_line.remaining_amount')
    # def _compute_amount_remaining(self):
    #     for record in self:
    #         if record.is_parent_budget and not record.parent_id:
    #             total_planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))
    #             remaining_amount = 0
    #             parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.id)])
    #             for parent_id in parent_ids:
    #                 total_practical_amount = sum(parent_id.crossovered_budget_line.mapped('practical_budget_amount'))
    #                 if total_practical_amount < 0:
    #                     total_practical_amount = total_practical_amount * -1
    #                 remaining_amount += total_planned_amount - total_practical_amount
    #                 record.amount_remaining = total_planned_amount - total_practical_amount
    #                 record.amount_remaining_temp = total_planned_amount - total_practical_amount
    #             # total_practical_amount = sum(parent_ids.crossovered_budget_line.mapped('practical_budget_amount'))
    #             # if total_practical_amount < 0:
    #             #     total_practical_amount = total_practical_amount * -1
    #             # record.amount_remaining = total_planned_amount - total_practical_amount
    #         elif record.is_parent_budget and record.parent_id:
    #             total_planned_amount = sum(record.crossovered_budget_line.mapped('planned_amount'))
    #             parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.id)])
    #             total_practical_amount = sum(parent_ids.crossovered_budget_line.mapped('practical_budget_amount'))
    #             if total_practical_amount < 0:
    #                 total_practical_amount = total_practical_amount * -1
                    
    #             record.amount_remaining = total_planned_amount - total_practical_amount
    #             record.amount_remaining_temp = total_planned_amount - total_practical_amount
    #         else:
    #             record.amount_remaining = sum(record.crossovered_budget_line.mapped('remaining_amount'))
    #             record.amount_remaining_temp = sum(record.crossovered_budget_line.mapped('remaining_amount'))

    # @api.onchange('is_parent_budget')
    # def _onchange_is_parent_budget(self):
    #     parent_budget = []
    #     if self.is_parent_budget:
    #         parent_budget = self.env['crossovered.budget'].search([]).ids
    #     else :
    #         parent_budget = self.env['crossovered.budget'].search([('is_parent_budget','=',True)]).ids
    #     return {'domain': {'parent_id': [('id', 'in', parent_budget)]}}
    
    @api.onchange('parent_id') 
    def _onchange_parent_id(self):
        if self.parent_id and self.date_from and self.date_to:
            if not (self.parent_id.date_from <= self.date_from <= self.parent_id.date_to) or not (self.parent_id.date_from <= self.date_to <= self.parent_id.date_to):
                raise ValidationError(_('You cannot change parent budget to %s because date period must equal or in period parent budget') % self.parent_id.name)
            elif (self.parent_id.date_from <= self.date_from <= self.parent_id.date_to) and (self.parent_id.date_from <= self.date_to <= self.parent_id.date_to):
                for line in self.crossovered_budget_line:
                    if line.general_budget_id not in self.parent_id.crossovered_budget_line.mapped('general_budget_id'):
                        raise ValidationError(_('Budgetary Position must be in parent budget'))
                    elif line.general_budget_id in self.parent_id.crossovered_budget_line.mapped('general_budget_id'):
                        parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', self.parent_id.id),('state','in',['validate','confirm','done'])])
                        crossovered_budget_line = parent_ids.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.general_budget_id.id)
                        if (line.planned_amount + sum(crossovered_budget_line.mapped('reserve_amount')) + sum(crossovered_budget_line.mapped('planned_amount'))) > self.parent_id.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.general_budget_id.id).planned_amount:
                            raise ValidationError(_('You cannot change parent budget to %s because allocate more than the planned amount.') % self.parent_id.name)
                        else:
                            raise ValidationError(_('You cannot change parent budget to %s') % (self.parent_id.name))

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    @api.depends('name')
    def _get_use_theoretical_achievement_config(self):
        is_use_theoretical_achievement = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_budget.accounting_budget_use_theoretical_achievement', False)
        self.is_use_theoretical_achievement = is_use_theoretical_achievement

    def action_budget_done(self):
        res = super(CrossoveredBudget, self).action_budget_done()
        for child in self.child_budget_ids:
            child.write({'state': 'done'})

        return res

    def action_budget_confirm(self):
        self._check_duplicate_budget()
        self._check_carryover_amount()
        # if self.parent_id:
        #     self.check_parent_budget_amount(self)
        for line in self.crossovered_budget_line:
                line._line_dates_between_budget_dates()

        res = super(CrossoveredBudget, self).action_budget_validate()
        if self.parent_id:
            if self.parent_id.state in ['cancel','draft']:
                raise ValidationError(_("You can’t approve this budget because %s is %s. Please select another budget") % (self.parent_id.name, self.parent_id.state))

        return res

    # def check_parent_budget_amount(self, budget_id):
    #     for line in budget_id.crossovered_budget_line:
    #         for parent_line in budget_id.parent_id.crossovered_budget_line:
    #             if parent_line.general_budget_id.id == line.general_budget_id.id:
    #                 if line.budget_amount > (parent_line.budget_amount - parent_line.reserve_amount):
    #                     raise ValidationError(_('You cannot allocate more than the parent budget amount.'))

    @api.onchange('is_parent_budget') 
    def _onchange_is_parent_budget(self):
        for budget in self:
            if budget.is_parent_budget:
                budget.account_tag_ids = False
                for line in budget.crossovered_budget_line:
                    line.account_tag_ids = False

    @api.model
    def create(self, vals):
        res = super(CrossoveredBudget, self).create(vals)
        res.check_backdate_period(res.date_to)

        return res

    def write(self, vals):
        for budget in self:
            date_to = vals.get('date_to')
            if vals.get('date_to') and budget.state != 'done':
                # budget.check_backdate_period(datetime.strptime(vals.get('date_to'), "%Y-%m-%d").date())
                if isinstance(date_to, str):
                    date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                budget.check_backdate_period(date_to)

            if vals.get('state') in ['to_approve','confirm','validate']:
                if not budget.crossovered_budget_line:
                    raise ValidationError(_('You have not added any budget lines. Please input the budget lines first.'))

                if budget.parent_id:
                    for line in budget.crossovered_budget_line:
                        parent_line = self.env['crossovered.budget.lines'].search([
                            ('general_budget_id', '=', line.general_budget_id.id),
                            ('crossovered_budget_id', '=', budget.parent_id.id)
                        ], limit=1)

                        same_budget_lines = self.env['crossovered.budget.lines'].search([
                            ('general_budget_id', '=', line.general_budget_id.id),
                            ('crossovered_budget_id', '=', budget.id)
                        ])

                        if sum(same_budget_lines.mapped('budget_amount')) > parent_line.available_to_child_amount:
                            raise ValidationError(_('You cannot allocate more than the parent budget amount.'))

        res = super(CrossoveredBudget, self).write(vals)
        return res

    def check_backdate_period(self, date_to):
        today = fields.Date.today()
        if date_to and today > date_to and self.state != 'done':
            raise ValidationError(_('Cannot create budget in backdate periods'))

    @api.onchange('date_from','date_to') 
    def _onchange_budget_date(self):
        for line in self.crossovered_budget_line:
            line.date_from = line.crossovered_budget_id.date_from
            line.date_to = line.crossovered_budget_id.date_to

    def _check_carryover_amount(self):
        for line in self.child_budget_carry_over_line_ids:
            line.budget_carry_over_id.crossover_budget_id._compute_amount_practical()
            if line.budget_carry_over_id.crossover_budget_id.amount_remaining <= 0:
                raise ValidationError(_('You cannot create the budget because it’s carry over from %s and %s’s remaining amount = 0' % (line.budget_carry_over_id.crossover_budget_id.name, line.budget_carry_over_id.crossover_budget_id.name)))


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    is_parent_budget = fields.Boolean(related='crossovered_budget_id.is_parent_budget')
    parent_analytic_account_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position')
    currency_company_id = fields.Many2one('res.currency', related='crossovered_budget_id.company_id.currency_id', string='Company Currency', readonly=True)
    reserve_amount = fields.Monetary('Child Budget', compute='_get_reserve_amount')
    reserve_amount_2 = fields.Monetary('Account Reserved', compute='_get_reserve_amount')
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_cb_rel', 'budget_id', 'tag_id', string="Analytic Group")
    filtered_budget_line = fields.Many2many('account.budget.post', store=False, compute='_get_budget_line')
    practical_budget_amount = fields.Monetary(string='Realized Amount', compute="_compute_budget_practical_amount", help="Amount really earned/spent.")
    practical_temp_budget = fields.Monetary('Realized Amount', store=True)
    remaining_amount = fields.Monetary(string='Remaining Amount',compute="_compute_budget_remaining_amount", help="Amount remaining to earn/spent.")
    remaining_temp_budget = fields.Monetary('Remaining Temp', store=True)
    theoritical_amount_2 = fields.Monetary(string='Theoretical Amount', compute='_compute_theoretical_amount_2',help="Amount you are supposed to have earned/spent at this date.")
    percentage_2 = fields.Float(string='Achievement',compute='_compute_percentage_2',help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    transfer_amount = fields.Float('Transfer Amount')
    carry_over_amount = fields.Monetary('Carry Over Amount', compute='_compute_carry_over_amount')
    change_amount = fields.Monetary('Budget Change Amount')
    budget_amount = fields.Monetary('Budget Amount', compute="_compute_budget_amount",)
    parent_id = fields.Many2one('crossovered.budget', 'Parent Budget', related="crossovered_budget_id.parent_id")
    budget_name = fields.Char('Budget Name', related="crossovered_budget_id.name")
    state = fields.Selection(related="crossovered_budget_id.state")
    child_purchase_amount = fields.Monetary('Child Purchase', compute='_get_child_purchase_amount')
    available_to_child_amount = fields.Monetary('Available Child Budget', compute='_get_available_to_child_amount')
    purchased_amount = fields.Monetary('Purchased Amount', compute='_get_child_purchase_amount')
    pr_reserved_amount = fields.Monetary('PR Reserved', compute='_get_child_purchase_amount')
    available_child_purchase_amount = fields.Monetary('Available Child Purchase', compute='_get_available_child_purchase_amount')


    def _get_child_purchase_amount(self):
        for line in self:
            if not line.crossovered_budget_id.is_parent_budget:
                domain = [
                    ('purchase_budget_id.parent_id','=',line.crossovered_budget_id.id),
                    ('product_budget','=',line.general_budget_id.id),
                    ('purchase_budget_id.state','in',['validate','done']),
                    ('date_from','>=',line.date_from),
                    ('date_to','<=',line.date_to),
                ]
                if line.account_tag_ids:
                    domain += [('account_tag_ids','in',line.account_tag_ids.ids)]
                budget_purchase_lines = self.env['budget.purchase.lines'].search(domain)
                line.child_purchase_amount = sum(budget_purchase_lines.mapped('planned_amount'))
                line.purchased_amount = sum(budget_purchase_lines.mapped('practical_amount'))
                line.pr_reserved_amount = sum(budget_purchase_lines.mapped('reserve_amount'))
            else:
                child_lines = line.crossovered_budget_id.child_budget_line_ids.filtered(lambda r: r.general_budget_id.id == line.general_budget_id.id)
                line.pr_reserved_amount = sum(child_lines.mapped('pr_reserved_amount'))
                line.purchased_amount = sum(child_lines.mapped('purchased_amount'))
                line.child_purchase_amount = sum(child_lines.mapped('child_purchase_amount'))

    def _get_available_to_child_amount(self):
        for line in self:
            if line.crossovered_budget_id.is_parent_budget:
                line.available_to_child_amount = line.budget_amount - line.reserve_amount
            else:
                line.available_to_child_amount = 0

    def _get_available_child_purchase_amount(self):
        for line in self:
            if not line.crossovered_budget_id.is_parent_budget:
                line.available_child_purchase_amount = line.budget_amount - (line.child_purchase_amount + line.reserve_amount_2 + line.practical_budget_amount)
            else:
                line.available_child_purchase_amount = 0

    def _compute_carry_over_amount(self):
        for line in self:
            final_carry_over_amount = 0

            budget_carry_over_lines = self.env['budget.carry.over.lines'].search([
                ('budget_carry_over_id.crossover_budget_id','=',line.crossovered_budget_id.id),
                ('budget_carry_over_id.state','=','confirm'),
                ('general_budget_id','=',line.general_budget_id.id),
                ('budget_carry_over_id.new_crossovered_budget_id.state','in',['confirm','validate','done']),
            ])
            for carry_line in budget_carry_over_lines:
                final_carry_over_amount -= carry_line.carry_over_amount

            budget_carry_over_lines = self.env['budget.carry.over.lines'].search([
                ('budget_carry_over_id.new_crossovered_budget_id','=',line.crossovered_budget_id.id),
                ('budget_carry_over_id.state','=','confirm'),
                ('general_budget_id','=',line.general_budget_id.id),
                # ('date_from','=',line.date_from),
                # ('date_to','=',line.date_to),
            ])
            for carry_line in budget_carry_over_lines:
                final_carry_over_amount += carry_line.carry_over_amount

            line.carry_over_amount = final_carry_over_amount

    @api.depends('planned_amount','carry_over_amount','transfer_amount','change_amount')
    def _compute_budget_amount(self):
        for record in self:
            record.budget_amount = record.planned_amount + record.carry_over_amount + record.transfer_amount + record.change_amount

    @api.onchange('general_budget_id')
    def _get_parent_id_analytic_account(self):
        if self.crossovered_budget_id.parent_id:
            list_of_analytic_account = []
            for rec in self.crossovered_budget_id.parent_id.crossovered_budget_line:
                list_of_analytic_account.append(rec.analytic_account_id.id)
            return {'domain': {'parent_analytic_account_id': [('id', 'in', list_of_analytic_account)]}}

    @api.depends('crossovered_budget_id', 'crossovered_budget_id.parent_id')
    def _get_budget_line(self):
        for record in self:
            if record.crossovered_budget_id.parent_id:
                line_ids = record.crossovered_budget_id.parent_id.crossovered_budget_line.mapped('general_budget_id')
                record.filtered_budget_line = [(6, 0, line_ids.ids)]
            else:
                line_ids = self.env['account.budget.post'].search([])
                record.filtered_budget_line = [(6, 0, line_ids.ids)]

    def _get_reserve_amount(self):
        for record in self:
            parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', record.crossovered_budget_id.id),('state','in',['validate','confirm','done'])])
            crossovered_budget_line = parent_ids.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == record.general_budget_id.id)
            record.reserve_amount = sum(crossovered_budget_line.mapped('budget_amount'))
            if record.crossovered_budget_id.is_parent_budget:
                record.reserve_amount_2 = sum(crossovered_budget_line.mapped('reserve_amount_2'))
            else:
                reserve_amount_2 = 0

                account_vouchers = self.env['account.voucher.line'].search([
                    ('voucher_id.state','in',['confirmed','to_approve']),
                    ('analytic_tag_ids','in',record.account_tag_ids.ids),
                    ('account_id','in',record.general_budget_id.account_ids.ids),
                    ('voucher_id.account_date','>=',record.date_from),
                    ('voucher_id.account_date','<=',record.date_to),
                ])
                for voucher in account_vouchers:
                    reserve_amount_2 += voucher.price_unit * voucher.quantity

                pettycash_vouchers = self.env['account.pettycash.voucher.wizard.line'].search([
                    ('line_id.state','=','approved'),
                    ('analytic_group_ids','in',record.account_tag_ids.ids),
                    ('expense_account','in',record.general_budget_id.account_ids.ids),
                    ('line_id.date','>=',record.date_from),
                    ('line_id.date','<=',record.date_to),
                ])
                for pettycash in pettycash_vouchers:
                    reserve_amount_2 += pettycash.price_unit * pettycash.quantity

                account_moves = self.env['account.move.line'].search([
                    ('move_id.state','in',['confirmed','to_approve']),
                    ('analytic_tag_ids','in',record.account_tag_ids.ids),
                    ('account_id','in',record.general_budget_id.account_ids.ids),
                    ('date','>=',record.date_from),
                    ('date','<=',record.date_to),
                    ('move_id.is_from_receiving_note','=',False),
                ])
                for move in account_moves:
                    reserve_amount_2 += move.amount_currency

                vendor_deposit = self.env['vendor.deposit'].search([
                    ('state','in',['confirmed','to_approve','approved']),
                    ('analytic_group_ids','in',record.account_tag_ids.ids),
                    ('deposit_account_id','in',record.general_budget_id.account_ids.ids),
                    ('payment_date','>=',record.date_from),
                    ('payment_date','<=',record.date_to),
                ])
                for vendor in vendor_deposit:
                    reserve_amount_2 += vendor.amount

                record.reserve_amount_2 = reserve_amount_2
    # @api.onchange('planned_amount')
    # def _onchange_planned_amount(self):
    #     parent_id = self.crossovered_budget_id.parent_id
    #     if not self.is_parent_budget and parent_id:
    #         parent_budget = self.env['crossovered.budget'].search([('id','=',self.crossovered_budget_id.parent_id.id),('state','!=', 'cancel')])
    #         for line in parent_budget.crossovered_budget_line:
    #             if line.general_budget_id.id == self.general_budget_id.id:
    #                 parent_planned_amount = line.planned_amount + line.transfer_amount
    #                 parent_reserve_amount = line.reserve_amount
    #                 if (self.planned_amount + parent_reserve_amount) > parent_planned_amount:
    #                     raise ValidationError(_('You cannot allocate more than parent planned amount.'))    
    #         # parent_planned_amount = sum(parent_budget.crossovered_budget_line.mapped('planned_amount'))
    #         # parent_reserve_amount = sum(parent_budget.crossovered_budget_line.mapped('reserve_amount'))
    #         # total_amount = self.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == budget_line.general_budget_id.id)
    #         # budget_allocation = self.crossovered_budget_id.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == budget_line.general_budget_id.id)
    #         # for line in budget_allocation:
    #         #     if line.id == self.id:
    #         #         parent_reserve_amount += line.planned_amount
                    
    #     elif self.is_parent_budget and parent_id:
    #         parent_budget = self.env['crossovered.budget'].search([('id','=',self.crossovered_budget_id.parent_id.id),('state','!=', 'cancel')])
    #         for line in parent_budget.crossovered_budget_line:
    #             if line.general_budget_id.id == self.general_budget_id.id:
    #                 parent_planned_amount = line.planned_amount + line.transfer_amount
    #                 parent_reserve_amount = line.reserve_amount
    #                 if (self.planned_amount + parent_reserve_amount) > parent_planned_amount:
    #                     raise ValidationError(_('You cannot allocate more than parent planned amount.'))
                    
                
    @api.depends('general_budget_id', 'crossovered_budget_id.account_tag_ids')
    def _compute_budget_practical_amount(self):
        for line in self:
            if line.crossovered_budget_state != 'done':
            # if line.crossovered_budget_state in ['draft','validate', 'done']:
                if line.crossovered_budget_id.is_parent_budget:
                    parent_ids = self.env['crossovered.budget'].search([('parent_id', '=', line.crossovered_budget_id.id),('state','!=','cancel')])
                    crossovered_budget_line = parent_ids.crossovered_budget_line.filtered(lambda r: r.general_budget_id.id == line.general_budget_id.id)
                    line.practical_budget_amount = sum(crossovered_budget_line.mapped('practical_budget_amount'))
                    line.practical_temp_budget = line.practical_budget_amount
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
                        
                        self.env.cr.execute(select, where_clause_params)
                        line.practical_budget_amount = self.env.cr.fetchone()[0] or 0.0
                        if line.practical_budget_amount < 0:
                            line.practical_budget_amount = line.practical_budget_amount * -1
                        line.practical_temp_budget = line.practical_budget_amount

                    else:
                        # aml_obj = self.env['account.move.line']
                        # domain = [('account_id', 'in',line.general_budget_id.account_ids.ids),
                        #         ('analytic_tag_ids', 'in', line.account_tag_ids.ids),
                        #         ('date', '>=', date_from),
                        #         ('date', '<=', date_to),
                        #         ('move_id.state', '=', 'posted')
                        #         ]
                        # where_query = aml_obj._where_calc(domain)
                        # aml_obj._apply_ir_rules(where_query, 'read')
                        # from_clause, where_clause, where_clause_params = where_query.get_sql()
                        # select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

                        # self.env.cr.execute(select, where_clause_params)
                        # line.practical_budget_amount = self.env.cr.fetchone()[0] or 0.0
                        # line.practical_temp_budget = line.practical_budget_amount
                        domain = [('account_id', 'in',line.general_budget_id.account_ids.ids),
                                ('analytic_tag_ids', 'in', line.account_tag_ids.ids),
                                ('date', '>=', date_from),
                                ('date', '<=', date_to),
                                ('move_id.state', '=', 'posted'),
                                ('move_id.is_from_receiving_note','=',False),
                                ]
                        aml_obj = self.env['account.move.line'].search(domain)
                        debit = sum(aml_obj.mapped('debit'))
                        credit = sum(aml_obj.mapped('credit'))
                        line.practical_budget_amount = credit - debit
                        if line.practical_budget_amount < 0:
                            line.practical_budget_amount = line.practical_budget_amount * -1
                        line.practical_temp_budget = line.practical_budget_amount
            else:
                line.practical_budget_amount=line.practical_temp_budget
                if line.practical_budget_amount < 0:
                    line.practical_budget_amount = line.practical_budget_amount * -1

    def _is_above_budget(self):
        for line in self:
            if line.theoritical_amount >= 0:
                line.is_above_budget = line.practical_budget_amount > line.theoritical_amount
            else:
                line.is_above_budget = line.practical_budget_amount < line.theoritical_amount
    
    @api.depends('date_to','date_from','paid_date','planned_amount')
    def _compute_theoretical_amount_2(self):
        # beware: 'today' variable is mocked in the python tests and thus, its implementation matter
        today = fields.Date.today()
        for line in self:
            if line.paid_date:
                if today <= line.paid_date:
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                if line.date_to and line.date_from:
                    line_timedelta = line.date_to - (line.date_from - timedelta(days=1))
                    elapsed_timedelta = today - (line.date_from - timedelta(days=1))

                    if elapsed_timedelta.days < 0:
                        # If the budget line has not started yet, theoretical amount should be zero
                        theo_amt = 0.00
                    elif line_timedelta.days > 0 and today < line.date_to:
                        # If today is between the budget line date_from and date_to
                        theo_amt = (elapsed_timedelta / line_timedelta) * line.budget_amount

                    else:
                        theo_amt = line.planned_amount
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount_2 = theo_amt

    @api.depends('practical_budget_amount','theoritical_amount_2')
    def _compute_percentage_2(self):
        for line in self:
            if line.theoritical_amount_2 != 0.00:
                line.percentage_2 = (line.reserve_amount_2 + line.pr_reserved_amount + line.practical_budget_amount + line.purchased_amount) / line.theoritical_amount_2
            else:
                line.percentage_2 = 0.00
    
    @api.depends('planned_amount', 'practical_budget_amount', 'transfer_amount', 'budget_amount')
    def _compute_budget_remaining_amount(self):
        for record in self:
            record._get_reserve_amount()
            record._compute_budget_practical_amount()
            if record.planned_amount < 0:
                record.planned_amount = record.planned_amount * -1
            if record.practical_budget_amount < 0:
                record.practical_budget_amount = record.practical_budget_amount * -1
            record.remaining_amount = record.budget_amount - record.reserve_amount_2 - record.practical_budget_amount - record.pr_reserved_amount - record.purchased_amount
            record.remaining_temp_budget = record.remaining_amount
   
    @api.constrains('planned_amount')
    def _check_planned_amount(self):
        for rec in self:
            if (rec.planned_amount + rec.carry_over_amount + rec.transfer_amount + rec.change_amount) <= 0:
                raise ValidationError(_('Budget amount must be greater than 0!'))

    def _line_dates_between_budget_dates(self):
        for rec in self:
            budget_date_from = rec.crossovered_budget_id.date_from
            budget_date_to = rec.crossovered_budget_id.date_to
            if rec.date_to < rec.date_from:
                raise ValidationError(_('End date cannot before the start date.'))
            if rec.date_from:
                date_from = rec.date_from
                if date_from < budget_date_from or date_from > budget_date_to:
                    raise ValidationError(_('"Start Date" of the budget line should be included in the Period of the budget'))
            if rec.date_to:
                date_to = rec.date_to
                if date_to < budget_date_from or date_to > budget_date_to:
                    raise ValidationError(_('"End Date" of the budget line should be included in the Period of the budget'))


class ExpenseRequestWarning(models.TransientModel):
    _name = "expense.request.warning"
    _description = "Expense Request Warning"
    
    # def default_get(self, fields):
    #     context = self._context
    #     result = super(ExpenseRequestWarning, self).default_get(fields)
    #     if context.get('warning_line_ids', []):
    #         result['warning_line_ids'] = context.get('warning_line_ids')
    #     return result
    
    name = fields.Html('Name')
    warning_line_ids = fields.One2many('expense.request.warning.line', 'warning_id', 'Product Details')
    
    def confirm_expense_request(self):
        context = self._context
        active_id = context.get('active_id')
        active_model = context.get('active_model')
        if active_model == 'account.voucher':
            is_use_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_other_income_approval_matrix', False)
            if is_use_approval_matrix:
                return self.env['account.voucher'].browse([active_id]).send_request_for_approval()
            else:
                # return self.env['account.voucher'].browse([active_id]).action_move_line_create()
                return self.env['account.voucher'].browse([active_id]).write({'state': 'confirmed'})
        elif active_model == 'account.pettycash.voucher.wizard':
            return self.env['account.pettycash.voucher.wizard'].browse([active_id]).send_request_for_approval()
        elif active_model == 'account.move':
            is_invoice_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_invoice_approval_matrix', False)
            if is_invoice_approval_matrix:
                return self.env['account.move'].browse([active_id]).send_request_for_approval()
            else:
                return self.env['account.move'].browse([active_id]).write({'state': 'confirmed'})
        elif active_model == 'vendor.deposit':
            is_cash_advance_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_cash_advance_approving_matrix', False)
            if is_cash_advance_approval_matrix:
                return self.env['vendor.deposit'].browse([active_id]).send_request_approval_cash_advance()
            else:
                return self.env['vendor.deposit'].browse([active_id]).write({'state': 'confirmed'})

        
class ExpenseRequestWarningLine(models.TransientModel):
    _name = "expense.request.warning.line"
    _description = "Expense Request Line Warning"
    
    warning_id = fields.Many2one('expense.request.warning', 'Warning')
    product_id = fields.Many2one('product.product', "Product")
    budgetary_position_id = fields.Many2one('account.budget.post', "Budgetary Position")
    account_id = fields.Many2one('account.account', "Account")
    expense_budget = fields.Float("Remaining Budget")
    planned_budget = fields.Float("Budget")
    used_budget = fields.Float("Used Budget")
    realized_amount = fields.Float("Realized Budget")

    def _get_approve_button_from_config(self):
        for record in self:
            is_other_income_approval_matrix = False
            if record.voucher_type == 'sale':
                is_other_income_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
                    'is_other_income_approval_matrix', False)
            elif record.voucher_type == 'purchase':
                is_other_income_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
                    'is_other_expense_approval_matrix', False)
            record.is_other_income_approval_matrix = is_other_income_approval_matrix
    

    

