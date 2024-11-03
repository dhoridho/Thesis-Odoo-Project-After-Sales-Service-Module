from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import json


class BudgetTransfer(models.Model):
    _name = "budget.transfer"

    name = fields.Char(string="Number", readonly=True, required=True, copy=False, default='New')


class CrossoveredBudgetTransfer(models.Model):
    _name = "crossovered.budget.transfer"
    _description = "Budget Transfer"
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

    name = fields.Char(string="Number", readonly=True, required=True, copy=False, default='/')
    source_budget_id = fields.Many2one('crossovered.budget', string='Source Budget', required=True)
    destination_budget_id = fields.Many2one('crossovered.budget', string='Destination Budget', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one('res.branch', 'Branch', check_company=True, domain=_domain_branch, default=_default_branch, readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    budget_transfer_line_ids = fields.One2many('crossovered.budget.transfer.line', 'budget_transfer_id', string="Budget Transfer Line")
    confirm_date = fields.Datetime('Confirm Date', readonly=True, copy=False)
    total_transfer_amount = fields.Float('Transfer Amount', compute='_compute_total_transfer_amount')
    currency_company_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency', readonly=True)
    budget_transfer_name = fields.Char(string="Budget Transfer Name", required=True)


    def _compute_total_transfer_amount(self):
        for budget in self:
            amount = 0
            for line in budget.budget_transfer_line_ids:
                amount += line.transfer_amount

            budget.total_transfer_amount = amount

    def action_confirm(self):
        for record in self:
            record.write({
                'state': 'confirm',
                'name': self.env['ir.sequence'].next_by_code('budget.transfer.seq'),
                'confirm_date': datetime.now()
            })

            total_transfer_amount = 0
            for line in record.budget_transfer_line_ids:
                source_budget_line = self.env['crossovered.budget.lines'].search([('crossovered_budget_id','=',line.source_budget_id.id),('general_budget_id','=',line.source_general_budget_id.id)], limit=1)
                
                if not line.source_budget_id.is_parent_budget and source_budget_line.available_child_purchase_amount != 0 and line.transfer_amount > source_budget_line.available_child_purchase_amount:
                    raise ValidationError(_('%s has been reserved and used. You cannot transfer bigger than child purchase, account reserved and realized amount.' % source_budget_line.crossovered_budget_id.name)) 

                total_transfer_amount += line.transfer_amount
                                
                if source_budget_line.crossovered_budget_id.is_parent_budget and total_transfer_amount > source_budget_line.available_to_child_amount:
                    raise ValidationError(_('%s is the parent budget. You cannot transfer bigger than the available child budget amount.' % source_budget_line.crossovered_budget_id.name)) 

                source_budget_line.transfer_amount -= line.transfer_amount

                if line.destination_budget_id.parent_id:
                    # child_budget_line = self.env['crossovered.budget.lines'].search([('general_budget_id','=',line.destination_general_budget_id.id),('crossovered_budget_id','=',line.destination_budget_id.id)])
                    # child_budget_amount = line.current_remaining_amount
                    
                    parent_budget_line = self.env['crossovered.budget.lines'].search([('general_budget_id','=',line.destination_general_budget_id.id),('crossovered_budget_id','=',line.destination_budget_id.parent_id.id)])
                    # parent_budget_amount = parent_budget_line.budget_amount - parent_budget_line.reserve_amount
                    parent_avail_child_amount = parent_budget_line.available_to_child_amount

                    # if line.transfer_amount > parent_budget_amount:
                        # raise ValidationError(_('%s is child budget. You cannot allocate more than parent budget amount!' % line.destination_budget_id.name))
                    if total_transfer_amount > parent_avail_child_amount:
                        raise ValidationError(_('%s is child budget. You cannot allocate more than parent budget amount.' % line.destination_budget_id.name))

                if source_budget_line.remaining_amount < 0:
                    raise ValidationError(_('Transfer Amount cannot bigger than Remaining Amount Source Budget.'))

                dest_budget_line = self.env['crossovered.budget.lines'].search([('crossovered_budget_id','=',line.destination_budget_id.id),('general_budget_id','=',line.destination_general_budget_id.id)], limit=1)
                dest_budget_line.transfer_amount += line.transfer_amount


class CrossoveredBudgetTransferLine(models.Model):
    _name = 'crossovered.budget.transfer.line'
    _description = 'Budget Transfer Line'


    budget_transfer_id = fields.Many2one('crossovered.budget.transfer', string='Budget Transfer')
    source_budget_id = fields.Many2one('crossovered.budget', related='budget_transfer_id.source_budget_id', string='Source Budget', store=True, readonly=True)
    source_general_budget_id = fields.Many2one('account.budget.post', string='Source Budgetary', required=True)
    source_general_budget_id_domain = fields.Char(string='Source Budgetary Position Domain', compute='_compute_general_budget_id_domain')
    source_remaining_amount = fields.Float('Source Amount', compute='_compute_remaining_amount', store=True)
    destination_budget_id = fields.Many2one('crossovered.budget', related='budget_transfer_id.destination_budget_id', string='Destination Budget', store=True, readonly=True)
    destination_general_budget_id = fields.Many2one('account.budget.post', string='Destination Budgetary', required=True)
    destination_general_budget_id_domain = fields.Char(string='Destination Budgetary Position Domain', compute='_compute_general_budget_id_domain')
    destination_remaining_amount = fields.Float('Destination Amount', compute='_compute_remaining_amount', store=True)
    transfer_amount = fields.Float('Transfer Amount', required=True)
    current_remaining_amount = fields.Float('Current Remaining Amount', compute='_compute_current_remaining_amount')
    currency_company_id = fields.Many2one('res.currency', related='budget_transfer_id.company_id.currency_id', string='Company Currency', readonly=True)
    budget_parent_number = fields.Char(string="Number", related='budget_transfer_id.name')
    budget_parent_name = fields.Char(string="Budget Transfer Name", related='budget_transfer_id.budget_transfer_name')


    @api.depends('source_budget_id','destination_budget_id')
    def _compute_general_budget_id_domain(self):
        source_budget_ids = []
        destination_budget_ids = []

        if not self.source_budget_id or not self.destination_budget_id:
            raise ValidationError(_('Please select Budget first!'))

        for line in self.source_budget_id.crossovered_budget_line:
            if line.remaining_amount > 0:
                source_budget_ids.append(line.general_budget_id.id)

        for line in self.destination_budget_id.crossovered_budget_line:
            destination_budget_ids.append(line.general_budget_id.id)

        self.source_general_budget_id_domain = json.dumps([('id','in',source_budget_ids)])
        self.destination_general_budget_id_domain = json.dumps([('id','in',destination_budget_ids)])

    @api.depends('source_budget_id','source_general_budget_id','destination_budget_id','destination_general_budget_id')
    def _compute_remaining_amount(self):
        for line in self:
            budget_line = self.env['crossovered.budget.lines'].search([('crossovered_budget_id','=',line.source_budget_id.id),('general_budget_id','=',line.source_general_budget_id.id)], limit=1)
            line.source_remaining_amount = budget_line.remaining_amount

            budget_line = self.env['crossovered.budget.lines'].search([('crossovered_budget_id','=',line.destination_budget_id.id),('general_budget_id','=',line.destination_general_budget_id.id)], limit=1)
            line.destination_remaining_amount = budget_line.remaining_amount

    @api.depends('transfer_amount','destination_remaining_amount')
    def _compute_current_remaining_amount(self):
        for line in self:
            line.current_remaining_amount = line.destination_remaining_amount + line.transfer_amount

    @api.constrains('transfer_amount')
    def _check_transfer_amount(self):
        for rec in self:
            if rec.transfer_amount > rec.source_remaining_amount:
                raise ValidationError(_('Transfer Amount cannot bigger than Remaining Amount Source Budget!'))