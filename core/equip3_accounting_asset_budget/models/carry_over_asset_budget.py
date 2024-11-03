from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class CarryOverAssetBudget(models.Model):
    _name = 'carry.over.asset.budget'
    _description = 'Carry Over Asset Budget'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, index=True, default=lambda self: _('New'))
    budget_reference = fields.Many2one('asset.budget.accounting', string='Budget Reference', domain="[('state', '=', 'done')]", required=True)
    is_parent_budget = fields.Boolean(string='Is Parent Budget', default=False)
    parent_id = fields.Many2one('carry.over.asset.budget', string='Parent Budget', domain="[('is_parent_budget', '=', True)]")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", required=True)
    date_from = fields.Date('Start Date', required=True, )
    date_to = fields.Date('End Date', required=True,)
    asset_budget_line_ids = fields.One2many('carry.over.asset.budget.line', 'asset_budget_id', string='Asset Budget Line')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    amount_planned = fields.Monetary('Planned Amount', compute='_compute_amount_planned')
    # amount_used = fields.Monetary('Used Amount', compute='_compute_amount_used')
    # amount_remaining = fields.Monetary('Remaining Amount', compute='_compute_amount_remaining')
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], string='Status', default='draft', readonly=True, copy=False, index=True, track_visibility='onchange')

    

    @api.depends('asset_budget_line_ids.planned_amount')
    def _compute_amount_planned(self):
        for budget in self:
            budget.amount_planned = sum(budget.asset_budget_line_ids.mapped('planned_amount'))

    # @api.depends('asset_budget_line_ids.used_amount')
    # def _compute_amount_used(self):
    #     for budget in self:
    #         budget.amount_used = sum(budget.asset_budget_line_ids.mapped('used_amount'))

    # @api.depends('asset_budget_line_ids.remaining_amount')
    # def _compute_amount_remaining(self):
    #     for budget in self:
    #         budget.amount_remaining = sum(budget.asset_budget_line_ids.mapped('remaining_amount'))

    @api.onchange('budget_reference')
    def _onchange_budget_reference(self):
        if self.budget_reference:
            # remaining_amount = self.env['asset.budget.accounting'].search([('id', '=', self.budget_reference.id)]).mapped('amount_remaining')
            if self.budget_reference.amount_remaining == 0:
                raise ValidationError(_('You cannot select this budget,because remaining amaount is 0 '))
        
            self.account_tag_ids = self.budget_reference.account_tag_ids
            self.date_from = self.budget_reference.date_from
            self.date_to = self.budget_reference.date_to
            self.asset_budget_line_ids = [(5, 0, 0)]
            for line in self.budget_reference.asset_budget_line_ids:
                self.asset_budget_line_ids = [(0, 0, {
                    'parent_analytic_account_id': line.parent_analytic_account_id.id,
                    'asset_budgetary_position_id': line.asset_budgetary_position_id.id,
                    'account_tag_ids': [(6, 0, line.account_tag_ids.ids)],
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'carry_over_amount': line.remaining_amount,
                    'final_amount': line.remaining_amount,
                })]

    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        for line in self.asset_budget_line_ids:
            line.date_from = self.date_from
            line.date_to = self.date_to

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
        for record in self:
            line_data = [(0,0,{
                'asset_budgetary_position_id': line.asset_budgetary_position_id.id,
                'account_tag_ids': [(6, 0, line.account_tag_ids.ids)],
                'date_from': line.date_from,
                'date_to': line.date_to,
                'planned_amount': line.planned_amount,
                'carry_over_amount': line.carry_over_amount,
            }) for line in record.asset_budget_line_ids]
            vals = {
                'name': record.name,
                'is_parent_budget': record.is_parent_budget,
                'parent_id': record.parent_id.id,
                'account_tag_ids': [(6, 0, record.account_tag_ids.ids)],
                'date_from': record.date_from,
                'date_to': record.date_to,
                'company_id': record.company_id.id,
                'currency_id': record.currency_id.id,
                'branch_id': record.branch_id.id,
                'asset_budget_line_ids': line_data,
            }
            self.env['asset.budget.accounting'].create(vals)

            for line in record.asset_budget_line_ids:
                budget_ref_id = self.env['asset.budget.accounting.line'].search([('asset_budget_id', '=', record.budget_reference.id), ('asset_budgetary_position_id', '=', line.asset_budgetary_position_id.id)])
                budget_ref_id.carry_over_amount -= line.carry_over_amount

        self.write({'state': 'confirm'})

    def action_validate(self):
        self.write({'state': 'validate'})

    def action_done(self):
        self.write({'state': 'done'})

class CarryOverAssetBudgetLine(models.Model):
    _name = 'carry.over.asset.budget.line'
    _description = 'Carry Over Asset Budget Line'

    asset_budget_id = fields.Many2one('carry.over.asset.budget', string='Asset Budget')
    parent_analytic_account_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    asset_budgetary_position_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups", required=True)
    date_from = fields.Date('Start Date', required=True, )
    date_to = fields.Date('End Date', required=True,)
    company_id = fields.Many2one('res.company', string='Company', required=True, related='asset_budget_id.company_id')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, related='asset_budget_id.currency_id')
    planned_amount = fields.Monetary('Planned Amount', required=True)
    carry_over_amount = fields.Monetary('Carry Over Amount')
    final_amount = fields.Monetary('Final Amount')

    def action_open_asset_budget_entries(self):
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

        return action
    
    @api.onchange('planned_amount')
    def _onchange_planned_amount(self):
        self.final_amount = self.planned_amount + self.carry_over_amount


    @api.onchange('date_from', 'date_to')
    def _onchange_date(self):
        if self.date_from < self.asset_budget_id.date_from or self.date_from > self.asset_budget_id.date_to:
            raise ValidationError(_('Start date” and “end date” of the Asset Budget Line should be included in the Period of the budget.'))
        
        if self.date_to < self.asset_budget_id.date_from or self.date_to > self.asset_budget_id.date_to:
            raise ValidationError(_('Start date” and “end date” of the Asset Budget Line should be included in the Period of the budget.'))

    # @api.depends('asset_budget_id', 'asset_budgetary_position_id', 'account_tag_ids', 'date_from', 'date_to')
    # def _compute_used_amount(self):
    #     for line in self:
    #         line.used_amount = 0.0
    #         if line.asset_budget_id.state != 'done':
    #             if line.asset_budget_id.is_parent_budget:
    #                 child_budgets = self.env['asset.budget.accounting'].search([('parent_id', '=', line.asset_budget_id.id)])
    #                 for child_budget in child_budgets:
    #                     for child_line in child_budget.asset_budget_line_ids:
    #                         if child_line.asset_budgetary_position_id == line.asset_budgetary_position_id:
    #                             line.used_amount += child_line.used_amount
    #             else:
    #                 acc_ids = line.account_tag_ids.ids
    #                 date_from = line.date_from
    #                 date_to = line.date_to

    #                 domain = [('analytic_group_id', 'in', acc_ids),
    #                           ('date_start', '>=', date_from),
    #                           ('date_stop', '<=', date_to)]
    #                 asset_obj = self.env['maintenance.repair.order'].search(domain)
    #                 for asset in asset_obj:
    #                     used_amount = asset.maintenance_materials_list_ids.mapped('price_subtotal')
    #                     line.used_amount += sum(used_amount)
    #                     # line.remaining_amount = line.planned_amount - line.used_amount
    #         else:
    #             line.used_amount = sum(line.asset_budget_id.asset_budget_line_ids.filtered(lambda x: x.asset_budgetary_position_id == line.asset_budgetary_position_id).mapped('used_amount'))
