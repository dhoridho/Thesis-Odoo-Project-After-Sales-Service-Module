from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json


class BudgetPurchaseCarryOver(models.Model):
    _name = "budget.purchase.carry.over"
    _description = "Budget Purchase Carry Over"
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

    name = fields.Char('Purchase Budget Name')
    budget_purchase_id = fields.Many2one('budget.purchase', string="Purchase Budget Reference")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups")
    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default=_default_branch)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    date_from = fields.Date('Start Date', default=fields.Date.context_today)
    date_to = fields.Date('End Date', default=fields.Date.context_today)
    parent_id = fields.Many2one('crossovered.budget', 'Budget Account Reference')
    is_parent_budget = fields.Boolean(string="Is Parent Budget", default=False)
    parent_budget_id = fields.Many2one('budget.purchase', 'Parent Budget')
    budget_purchase_carry_over_line_ids = fields.One2many('budget.purchase.carry.over.lines', 'budget_purchase_carry_over_id', string="Budget Lines")
    total_planned_amount = fields.Float(compute='_compute_total_amount',string="Planned Amount")
    total_carry_over_amount = fields.Float(compute='_compute_total_amount',string="Carry Over Amount")
    total_final_planned_amount = fields.Float(compute='_compute_total_amount',string="Final Budget Amount")
    state = fields.Selection([
        ('draft', 'Draft'),         
        ('confirm', 'Confirmed')
    ], 'Status', default='draft', store=True, readonly=True, copy=False, tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    new_budget_purchase_id = fields.Many2one('budget.purchase', string="New Purchase Budget Reference")


    @api.depends('budget_purchase_carry_over_line_ids.planned_amount','budget_purchase_carry_over_line_ids.carry_over_amount','budget_purchase_carry_over_line_ids.final_planned_amount')
    def _compute_total_amount(self):
        for data in self:
            total_planned_amount = total_carry_over_amount = total_final_planned_amount = 0

            if data.budget_purchase_carry_over_line_ids:
                total_planned_amount += sum([line.planned_amount for line in data.budget_purchase_carry_over_line_ids])
                total_carry_over_amount += sum([line.carry_over_amount for line in data.budget_purchase_carry_over_line_ids])
                total_final_planned_amount += sum([line.final_planned_amount for line in data.budget_purchase_carry_over_line_ids])
            
            data.total_planned_amount = total_planned_amount
            data.total_carry_over_amount = total_carry_over_amount
            data.total_final_planned_amount = total_final_planned_amount

    def action_confirm(self):
        for record in self:
            vals = {
                'name': record.name,
                'is_parent_budget': record.is_parent_budget,
                'parent_id': record.parent_id.id,
                'account_tag_ids': record.account_tag_ids.ids,
                'date_from': record.date_from,
                'date_to': record.date_to,
                'company_id': record.company_id.id,
                'branch_id': record.branch_id.id,
            }
            budget_purchase = self.env['budget.purchase'].create(vals)

            record.write({'state': 'confirm', 'new_budget_purchase_id': budget_purchase.id})

            for line in record.budget_purchase_carry_over_line_ids:
                if line.carry_over_amount <= 0:
                    raise ValidationError("Carry over amount must be greater than 0!")
                if line.carry_over_amount > line.remaining_amount:
                    raise ValidationError("Carry over amount cannot be greater than remaining amount!")
                if line.final_planned_amount <= 0:
                    raise ValidationError("Final budget amount must be greater than 0!")

                if not record.budget_purchase_id.is_parent_budget and record.budget_purchase_id.parent_id:
                    crossovered_budget_lines = self.env['crossovered.budget.lines'].search(
                        [('general_budget_id', '=', line.product_budget.id),
                         ('general_budget_id', '=', line.product_budget.id),
                         ('crossovered_budget_id', '=', record.budget_purchase_id.parent_id.id)])
                    for budget_line in crossovered_budget_lines:
                        if line.final_planned_amount > budget_line.planned_amount:
                            raise ValidationError("%s is child budget. You cannot allocate more than the budget account reference amount." % record.budget_purchase_id.name)

                if not record.budget_purchase_id.is_parent_budget and record.budget_purchase_id.parent_budget_id:
                    parent_purchase_budget_line = self.env['budget.purchase.lines'].search([
                        ('purchase_budget_id','=',record.budget_purchase_id.parent_budget_id.id),
                        ('group_product_id','=',line.group_product_id.id),
                        ('product_id','=',line.product_id.id),
                        ('product_budget', '=', line.product_budget.id),
                        # ('account_tag_ids','in',line.account_tag_ids.ids),
                        ('date_from','<=',line.date_from),
                        ('date_to','>=',line.date_to),
                    ])
                    if parent_purchase_budget_line and line.final_planned_amount > parent_purchase_budget_line.avail_amount:
                        raise ValidationError("%s is child budget. You cannot allocate more than the parent amount." % record.budget_purchase_id.name)

                vals = {
                    'product_budget': line.product_budget.id,
                    'group_product_id': line.group_product_id.id,
                    'product_id': line.product_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'planned_amount': line.final_planned_amount,
                    'purchase_budget_id': budget_purchase.id,
                    'is_carry_over': True,
                }
                budget_purchase_line = self.env['budget.purchase.lines'].create(vals)
                line.write({'new_budget_purchase_line_id': budget_purchase_line.id})

    @api.onchange('date_from','date_to') 
    def _onchange_budget_date_period(self):
        for line in self.budget_purchase_carry_over_line_ids:
            line.date_from = line.budget_purchase_carry_over_id.date_from
            line.date_to = line.budget_purchase_carry_over_id.date_to

    @api.onchange('account_tag_ids')
    def _onchange_account_tag_ids(self):
        for line in self.budget_purchase_carry_over_line_ids:
            line.account_tag_ids = line.budget_purchase_carry_over_id.account_tag_ids.ids

    @api.onchange('budget_purchase_id')
    def _onchange_budget_purchase_id(self):
        data = [(5, 0, 0)]
        for record in self:
            record.is_parent_budget = record.budget_purchase_id.is_parent_budget
            record.parent_id = record.budget_purchase_id.parent_id
            record.branch_id = record.budget_purchase_id.branch_id or self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id
            record.account_tag_ids = record.budget_purchase_id.account_tag_ids

            for line in record.budget_purchase_id.purchase_budget_line:
                data.append((0, 0, {
                    'product_budget': line.product_budget.id,
                    'group_product_id': line.group_product_id.id,
                    'product_id': line.product_id.id,
                    'account_tag_ids': line.account_tag_ids.ids,
                    'carry_over_amount': line.remaining_amount,
                    'remaining_amount': line.remaining_amount,
                    'date_from': record.date_from,
                    'date_to': record.date_to,
                }))
            record.budget_purchase_carry_over_line_ids = data

    def unlink(self):
        for record in self:
            if record.state == 'confirm':
                raise ValidationError(_('You cannot delete in state %s.') % record.state)
        return super(BudgetPurchaseCarryOver, self).unlink()


class BudgetPurchaseCarryOverLines(models.Model):
    _name = "budget.purchase.carry.over.lines"
    _description = "Budget Purchase Carry Over Lines"


    budget_purchase_carry_over_id = fields.Many2one('budget.purchase.carry.over', string='Carry Over Purchase Budget')
    product_budget = fields.Many2one('account.budget.post', 'Budgetary Position')
    group_product_id = fields.Many2one('account.product.group', string="Group of Product")
    product_id = fields.Many2one('product.product', string="Product")
    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Groups")
    account_tag_ids_domain = fields.Char(string='Analytic Groups Domain', compute='_compute_account_tag_ids_domain')
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    planned_amount = fields.Monetary('Planned Amount')
    carry_over_amount = fields.Monetary('Carry Over Amount')
    final_planned_amount = fields.Monetary('Final Budget Amount', compute='_compute_final_planned_amount')
    remaining_amount = fields.Monetary('Remaining Amount')
    currency_id = fields.Many2one('res.currency', related='budget_purchase_carry_over_id.currency_id')
    is_parent_budget = fields.Boolean(string="Is Parent Budget", related='budget_purchase_carry_over_id.is_parent_budget')
    budget_carry_over_name = fields.Char('Purchase Budget Name', related="budget_purchase_carry_over_id.name")
    budget_purchase_id = fields.Many2one('budget.purchase', string="Purchase Budget Reference", related="budget_purchase_carry_over_id.budget_purchase_id")
    new_budget_purchase_id = fields.Many2one('budget.purchase', string="New Purchase Budget Reference", related="budget_purchase_carry_over_id.new_budget_purchase_id")
    new_budget_purchase_id_state = fields.Selection(related='new_budget_purchase_id.state')
    new_budget_purchase_line_id = fields.Many2one('budget.purchase.lines', string="New Budget Purchase Line")
    new_budget_purchase_line_account_tag_ids = fields.Many2many(related='new_budget_purchase_line_id.account_tag_ids')
    new_budget_purchase_line_date_from = fields.Date(related='new_budget_purchase_line_id.date_from')
    new_budget_purchase_line_date_to = fields.Date(related='new_budget_purchase_line_id.date_to')
    group_product_id_domain = fields.Char(string='GoP Domain', compute='_compute_product_domain')
    product_id_domain = fields.Char(string='Product Domain', compute='_compute_product_domain')
    product_budget_domain = fields.Char(string='Budgetary Domain', compute='_compute_product_domain')


    @api.depends('budget_purchase_carry_over_id.budget_purchase_id')
    def _compute_product_domain(self):
        group_product_ids = []
        product_ids = []
        budget_ids = []
        for line in self.budget_purchase_carry_over_id.budget_purchase_id.purchase_budget_line:
            group_product_ids.append(line.group_product_id.id)
            product_ids.append(line.product_id.id)
            budget_ids.append(line.product_budget.id)

        self.group_product_id_domain = json.dumps([('id','in',group_product_ids)])
        self.product_id_domain = json.dumps([('id','in',product_ids)])
        self.product_budget_domain = json.dumps([('id','in',budget_ids)])

    @api.depends('planned_amount', 'carry_over_amount')
    def _compute_final_planned_amount(self):
        for record in self:
            record.final_planned_amount = record.planned_amount + record.carry_over_amount

    @api.depends('budget_purchase_carry_over_id.account_tag_ids')
    def _compute_account_tag_ids_domain(self):
        for record in self:
            record.account_tag_ids_domain = json.dumps([('id','in',record.budget_purchase_carry_over_id.account_tag_ids.ids)])

    @api.model
    def create(self, vals):
        res = super(BudgetPurchaseCarryOverLines, self).create(vals)
        for line in res.budget_purchase_carry_over_id.budget_purchase_carry_over_line_ids:
            if res.id != line.id:
                if vals.get('group_product_id') and vals['group_product_id'] == line.group_product_id.id:
                    raise ValidationError("Group of Product %s already exists in lines" % line.group_product_id.name)
                if vals.get('product_id') and vals['product_id'] == line.product_id.id:
                    raise ValidationError("Product %s already exists in lines" % line.product_id.name)
                if vals.get('product_budget') and vals['product_budget'] == line.product_budget.id:
                    raise ValidationError("Budgetary Position %s already exists in lines" % line.product_budget.name)
        return res

    def write(self, vals):
        if vals.get('group_product_id') or vals.get('product_id') or vals.get('product_budget'):
            for rec in self:
                for line in rec.budget_purchase_carry_over_id.budget_purchase_carry_over_line_ids:
                    if vals.get('group_product_id') and vals['group_product_id'] == line.group_product_id.id:
                        raise ValidationError("Group of Product %s already exists in lines" % line.group_product_id.name)
                    if vals.get('product_id') and vals['product_id'] == line.product_id.id:
                        raise ValidationError("Product %s already exists in lines" % line.product_id.name)
                    if vals.get('product_budget') and vals['product_budget'] == line.product_budget.id:
                        raise ValidationError("Budgetary Position %s already exists in lines" % line.product_budget.name)
        res = super(BudgetPurchaseCarryOverLines, self).write(vals)
        return res

    @api.onchange('group_product_id','product_id','product_budget')
    def onchange_product(self):
        for rec in self:
            purchase_budget_line = self.env['budget.purchase.lines'].search([
                ('group_product_id','=',rec.group_product_id.id),
                ('product_id','=',rec.product_id.id),
                ('product_budget','=',rec.product_budget.id),
                ('purchase_budget_id','=',rec.budget_purchase_carry_over_id.budget_purchase_id.id),
            ], limit=1)

            rec.carry_over_amount = purchase_budget_line.remaining_amount