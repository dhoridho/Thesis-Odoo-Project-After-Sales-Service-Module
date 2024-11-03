from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AssetBudgetTransfer(models.Model):
    _name = 'asset.budget.transfer'
    _description = 'Asset Budget Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'


    def source_domain(self):
        zero_amount = []
        source_budget_ids = self.env['asset.budget.accounting'].search([('state', 'in', ['validate', 'done']),('amount_remaining','!=',0)])
        for source_budget_id in source_budget_ids:
            if source_budget_id.amount_remaining == 0:
                zero_amount.append(source_budget_id.id)
        return [('id','not in',zero_amount)]


    name = fields.Char(string='Name', required=True, readonly=True, copy=False, default='New')
    asset_budget_transfer_name = fields.Char(string='Budget Transfer Name', required=True)
    source_budget_id = fields.Many2one('asset.budget.accounting', string='Source Budget', required=True, domain="[('state', 'in', ('validate', 'done')),('amount_remaining_check','>',0)]")
    destination_budget_id = fields.Many2one('asset.budget.accounting', string='Destination Budget', required=True, domain="[('state', '=', 'validate')]")
    date = fields.Date(string='Confirm Date', required=True, default=fields.Date.context_today)
    asset_budget_transfer_line_ids = fields.One2many('asset.budget.transfer.line', 'asset_budget_transfer_id', string='Budget Transfer Line', copy=True)
    total_transfer_amount = fields.Monetary(string='Total Transfer Amount', compute='_compute_total_transfer_amount')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', readonly=True, copy=False, index=True, track_visibility='onchange')

    
    @api.depends('asset_budget_transfer_line_ids.transfer_amount')
    def _compute_total_transfer_amount(self):
        for budget in self:
            amount = 0
            for line in budget.asset_budget_transfer_line_ids:
                amount += line.transfer_amount

            budget.total_transfer_amount = amount
    
    def action_reject(self):
        self.write({'state': 'reject'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def request_approval(self):
        self.write({'state': 'to_approve'})

    def action_approve(self):
        self.write({'state': 'confirm'})

    def action_confirm(self):
        for record in self:
            for line in record.asset_budget_transfer_line_ids:
                source_asset_budget_line = line.source_asset_budget_line_id
                source_asset_budget_line.transfer_amount -= line.transfer_amount

                destination_asset_budget_line = line.destination_asset_budget_line_id
                destination_asset_budget_line.transfer_amount += line.transfer_amount

            record.write({'state': 'confirm',
                        'name': self.env['ir.sequence'].next_by_code('asset.budget.transfer.seq')})

    # def action_validate(self):
        # self.write({'state': 'validate'})

        # for line in self.asset_budget_transfer_line_ids:
        #     source_asset_budget_line = line.source_asset_budget_line_id
        #     source_asset_budget_line.transfer_amount -= self.asset_budget_transfer_line_ids.transfer_amount

        #     destination_asset_budget_line = line.destination_asset_budget_line_id
        #     destination_asset_budget_line.transfer_amount += self.asset_budget_transfer_line_ids.transfer_amount

        # self.write({'state': 'validate'})
            

    def action_done(self):
        self.write({'state': 'done'})

class AssetBudgetTransferLine(models.Model):
    _name = 'asset.budget.transfer.line'
    _description = 'Asset Budget Transfer Line'

    asset_budget_transfer_id = fields.Many2one('asset.budget.transfer', string='Budget Transfer', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='asset_budget_transfer_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='asset_budget_transfer_id.currency_id', store=True, readonly=True)
    asset_source_budget_id = fields.Many2one('asset.budget.accounting', related='asset_budget_transfer_id.source_budget_id', string='Source Budget Line', store=True, readonly=True)
    source_asset_budget_line_id = fields.Many2one('asset.budget.accounting.line', string='Source Asset Budget Line', required=True, domain="[('asset_budget_id', '=', asset_source_budget_id)]")
    # source_remaining_amount = fields.Monetary(string='Source Remaining Amount', related='source_asset_budget_line_id.remaining_amount', store=True, readonly=True)
    source_remaining_amount = fields.Monetary(string='Source Remaining Amount', readonly=True)
    asset_destination_budget_id = fields.Many2one('asset.budget.accounting', related='asset_budget_transfer_id.destination_budget_id', string='Destination Budget Line', store=True, readonly=True)
    destination_asset_budget_line_id = fields.Many2one('asset.budget.accounting.line', string='Destination Asset Budget Line', required=True, domain="[('asset_budget_id', '=', asset_destination_budget_id)]")
    # destination_remaining_amount = fields.Monetary(string='Destination Remaining Amount', related='destination_asset_budget_line_id.remaining_amount', store=True, readonly=True)
    destination_remaining_amount = fields.Monetary(string='Destination Remaining Amount', readonly=True)
    transfer_amount = fields.Monetary(string='Transfer Amount', required=True)
    current_remaining_amount = fields.Monetary(string='Current Remaining Amount', compute='_compute_current_remaining_amount', readonly=True)


    @api.onchange('destination_asset_budget_line_id')
    def _onchange_destination_asset_budget_line_id(self):
        remaining_amount = self.destination_asset_budget_line_id.remaining_amount
        self.destination_remaining_amount = remaining_amount

    @api.onchange('source_asset_budget_line_id')
    def _onchange_source_asset_budget_line_id(self):
        remaining_amount = self.source_asset_budget_line_id.remaining_amount
        self.source_remaining_amount = remaining_amount


    @api.depends('destination_remaining_amount', 'transfer_amount')
    def _compute_current_remaining_amount(self):
        for line in self:
            line.current_remaining_amount = line.destination_remaining_amount + line.transfer_amount

    # @api.onchange('destination_asset_budget_line_id')
    # def _onchange_destination_asset_budget_line_id(self):
    #     if self.destination_asset_budget_line_id.asset_budgetary_position_id != self.source_asset_budget_line_id.asset_budgetary_position_id:
    #         raise ValidationError(_('Destination budgetary position must be the same as the source budgetary position, please select another destination budgetary position or change the source budgetary position.'))


    @api.onchange('transfer_amount')
    def _onchange_transfer_amount(self):
        if self.transfer_amount > self.source_remaining_amount:
            raise ValidationError(_('Transfer amount must be less than or equal to the source remaining amount.'))

