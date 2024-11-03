from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AssetBudgetChangeRequest(models.Model):
    _name = 'asset.budget.change.request'
    _description = 'Asset Budget Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'asset_budget_id'

    requester_id = fields.Many2one('res.users', string='Requester', default=lambda self: self.env.user, required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    asset_budget_id = fields.Many2one('asset.budget.accounting', string='Asset Budget', required=True, domain="[('state', 'in', ['confirm', 'validate'])]")
    asset_budget_line_ids = fields.One2many('asset.budget.change.request.line', 'asset_budget_change_request_id', string='Asset Budget Change Request Line', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('confirm', 'Confirmed'),
        ('approved', 'Approved'),
        ('validate', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
        ('reject', 'Rejected'),
    ], string='Status', default='draft', readonly=True, copy=False, index=True, track_visibility='onchange')
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')


    @api.onchange('asset_budget_id')
    def _onchange_asset_budget_id(self):
        budget_line_list = [(5, 0, 0)]
        for req in self:
            req.write({
                'date_from': req.asset_budget_id.date_from,
                'date_to': req.asset_budget_id.date_to,
                'account_tag_ids': req.asset_budget_id.account_tag_ids,
                'branch_id': req.asset_budget_id.branch_id,
            })
            for line in req.asset_budget_id.asset_budget_line_ids:
                budget_line_list.append((0, 0, {
                    'asset_budgetary_position_id': line.asset_budgetary_position_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'planned_amount': line.planned_amount,
                    'current_amount': line.remaining_amount,
                    'new_amount': line.remaining_amount,
                }))
            req.asset_budget_line_ids = budget_line_list

    def action_reject(self):
        self.write({'state': 'reject'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def request_approval(self):
        self.write({'state': 'to_approve'})

    def action_approve(self):
        self.write({'state': 'confirm'})

    def action_confirm(self):
        for req in self:
            req.asset_budget_id.write({
                'account_tag_ids': req.account_tag_ids.ids,
                'date_from': req.date_from,
                'date_to': req.date_to,
                'branch_id': req.branch_id.id,
            })
            req.asset_budget_id.asset_budget_line_ids = False

            for line in req.asset_budget_line_ids:
                self.env['asset.budget.accounting.line'].create({
                    'asset_budget_id': req.asset_budget_id.id,
                    'asset_budgetary_position_id': line.asset_budgetary_position_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'planned_amount': line.planned_amount,
                    'change_request_amount': line.new_amount - line.current_amount,
                })

        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_validate(self):
        # self.write({'state': 'validate'})

        # for line in self.asset_budget_line_ids:
        #     diff_amount = line.new_amount - line.current_amount
        #     asset_budget_line = self.asset_budget_id.asset_budget_line_ids.filtered(lambda x: x.asset_budgetary_position_id == line.asset_budgetary_position_id)
        #     asset_budget_line.change_request_amount += diff_amount
        self.write({'state': 'validate'})

    def action_done(self):
        self.write({'state': 'done'})

class AssetBudgetChangeRequestLine(models.Model):
    _name = 'asset.budget.change.request.line'
    _description = 'Asset Budget Change Request Line'

    asset_budget_change_request_id = fields.Many2one('asset.budget.change.request', string='Asset Budget Change Request', ondelete='cascade')
    asset_budgetary_position_id = fields.Many2one('maintenance.equipment', string='Asset')
    planned_amount = fields.Monetary(string='Planned Amount')
    current_amount = fields.Monetary(string='Current Budget Amount')
    new_amount = fields.Monetary(string='New Budget Amount', required=True)
    company_id = fields.Many2one('res.company', string='Company', related='asset_budget_change_request_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='asset_budget_change_request_id.currency_id', store=True, readonly=True)
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group") 
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')