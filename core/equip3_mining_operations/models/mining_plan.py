import datetime
from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from calendar import monthrange

MONTH_NAMES = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'
]

OPERATION_NAMES =  [
    'overburden', 'coal_getting','hauling', 'crushing'
]


class MiningPlan(models.Model):
    _name = 'mining.plan'
    _description = 'Mining Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mining.plan', sequence_date=None) or _('New')
        return super(MiningPlan, self).create(vals)

    @api.constrains('year', 'state')
    def _check_year(self):
        for record in self:
            count = self.search_count([
                ('state', '=', "confirm"),
                ('operation_id', '=', record.operation_id.id),
                ('year', '=', record.year),
                ('id', '!=', record.id)
            ])
            if count:
                raise ValidationError("There is another Plan for the same year.")

    # @api.depends('company_id')
    # def _compute_allowed_operations(self):
    #     for record in self:
    #         allowed_operation_ids = []
    #         company_id = record.company_id
    #         if company_id:
    #             for operation_name in OPERATION_NAMES:
    #                 if company_id[operation_name]:
    #                     ref = self.env.ref('equip3_mining_operations.mining_operation_%s' % operation_name)
    #                     allowed_operation_ids.append(ref.id)
    #         record.allowed_operation_two_ids = [(6, 0, allowed_operation_ids)]

    @api.depends('month_ids', 'month_ids.work_days')
    def _compute_total(self):
        for record in self:
            month_ids = record.month_ids
            record.work_days = sum(month_ids.mapped('work_days'))

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.model
    def _default_month_ids(self):
        return [(0, 0, {
            'sequence': sequence,
        }) for sequence in range(len(MONTH_NAMES))]

    @api.depends('month_ids', 'month_ids.adjusted_monthly_target')
    def _compute_adjusted_target(self):
        for record in self:
            record.adjusted_target = sum(record.month_ids.mapped('adjusted_monthly_target'))

    name = fields.Char(required=True, copy=False, readonly=True, default=_('New'), tracking=True, string='Reference')

    mining_site_id = fields.Many2one(
        comodel_name='mining.site.control',
        string='Mining Site',
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('branch_id', '=', branch_id)]")

    allowed_operation_ids = fields.Many2many(
        comodel_name='mining.operations')
    
    allowed_operation_two_ids = fields.Many2many(
        comodel_name='mining.operations.two')

    operation_id = fields.Many2one(
        comodel_name='mining.operations',
        string='Operation',
        domain="[('id', 'in', allowed_operation_ids)]",
        tracking=True)

    operation_two_id = fields.Many2one(
        comodel_name='mining.operations.two',
        string='Operation',
        domain="[('id', 'in', allowed_operation_two_ids)]",
        required=True,
        tracking=True,
        readonly=True, 
        states={'draft': [('readonly', False)]})

    year = fields.Date(
        string='Year', 
        default=lambda self: fields.Date.today(), 
        required=True, 
        tracking=True,
        readonly=True, 
        states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        comodel_name='res.company', 
        string='Company', 
        default=lambda self: self.env.company, 
        readonly=True, 
        required=True)

    is_branch_required = fields.Boolean(related='company_id.show_branch')

    branch_id = fields.Many2one(
        comodel_name='res.branch', 
        string='Branch', 
        default=_default_branch, 
        domain=_domain_branch,
        readonly=True,
        states={'draft': [('readonly', False)]})

    create_uid = fields.Many2one(
        comodel_name='res.users', 
        string='Created By', 
        default=lambda self: self.env.user, 
        tracking=True)

    month_ids = fields.One2many(
        comodel_name='mining.plan.month',
        inverse_name='plan_id',
        string='Monthly Target',
        default=_default_month_ids,
        readonly=True,
        states={'draft': [('readonly', False)]})

    work_days = fields.Integer(string='Work Days', compute=_compute_total)

    product_id = fields.Many2one(
        comodel_name='product.product', 
        string='Product', 
        tracking=True,
        readonly=True)

    uom_id = fields.Many2one(
        comodel_name='uom.uom', 
        string='Unit of Measure', 
        tracking=True,
        readonly=True)

    initial_target = fields.Float(
        digits='Product Unit of Measure', 
        string='Initial Target', 
        tracking=True,
        readonly=True, 
        required=True,
        states={'draft': [('readonly', False)]})

    initial_uom_id = fields.Many2one(
        comodel_name='uom.uom', 
        string='Initial Target UoM', 
        tracking=True,
        readonly=True, 
        required=True,
        states={'draft': [('readonly', False)]})

    adjusted_target = fields.Float(
        digits='Product Unit of Measure', 
        string='Adjusted Target', 
        tracking=True,
        readonly=True, 
        states={'draft': [('readonly', False)]},
        compute=_compute_adjusted_target)

    adjusted_uom_id = fields.Many2one(
        comodel_name='uom.uom', 
        string='Adjusted Target UoM', 
        tracking=True,
        readonly=True) 

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')
    ], default='draft', string='Status')

    #technical fields
    monthly_plan_ids = fields.One2many(
        comodel_name='mining.planning',
        inverse_name='annual_id',
        string='Monthly Plans')


    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        if not self.operation_id or not self.company_id:
            return False
        operations = {
            self.env.ref('equip3_mining_operations.mining_operation_%s' % name).id: self.company_id['%s_uom' % name].id
            for name in OPERATION_NAMES
        }
        self.month_ids.update({'uom_id': operations[self.operation_id.id]})

    @api.onchange('year')
    def _onchange_year(self):
        self.month_ids.update({'year': self.year})
    
    @api.onchange('mining_site_id','allowed_operation_two_ids')
    def _onchange_mining_site_id(self):
        shelter = []
        self.allowed_operation_two_ids = None
        if self.mining_site_id:
            shelter = self.mining_site_id.operation_ids.ids
            self.allowed_operation_two_ids = [(6, 0, shelter)]
            
    @api.onchange('operation_two_id','month_ids')
    def _onchange_operation_two_id(self):
        if self.operation_two_id:
            for line in self.month_ids:
                line.uom_id = self.operation_two_id.uom_id.id

    @api.onchange('operation_two_id')
    def _onchange_operation(self):
        operation = self.operation_two_id
        self.product_id = operation and operation.primary_product_id.id or False
        self.initial_uom_id = operation and operation.uom_id.id or False
        self.adjusted_uom_id = operation and operation.uom_id.id or False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id and self.product_id.uom_id.id or False

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        self.month_ids.update({'uom_id': self.uom_id and self.uom_id.id or False})

    @api.onchange('initial_target', 'year')
    def _onchange_initial_target(self):
        year = self.year and self.year.year or 0
        total_work_days = sum([monthrange(year, i)[1] for i in range(1, 13)])
        for month in self.month_ids:
            initial_monthly_target = (self.initial_target / total_work_days) * month.work_days
            month.initial_monthly_target = initial_monthly_target
            month.adjusted_monthly_target = initial_monthly_target

    def _prepare_monthly_planning_values(self):
        self.ensure_one()
        today = fields.Date.today()
        year = self.year.year
        months = dict(self.env['mining.plan.month'].fields_get(allfields=['name'])['name']['selection'])
        return [{
            'name': '%s, %s' % (months.get(line.name), year),
            'month': line.name,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'mining_site_id': self.mining_site_id.id,
            'mining_operation_id': self.operation_two_id.id,
            'year_month': today.replace(year=year, month=i+1, day=1),
            'product_id': self.product_id.id,
            'uom_id': self.uom_id.id,
            'initial_target': line.initial_monthly_target,
            'initial_uom_id': self.operation_two_id.uom_id.id,
            'adjusted_uom_id': self.operation_two_id.uom_id.id,
            'annual_month_id': line.id
        } for i, line in enumerate(self.month_ids)]

    def action_confirm(self):
        self.ensure_one()

        values = self._prepare_monthly_planning_values()
        self.monthly_plan_ids = self.env['mining.planning'].create(values)
        for monthly in self.monthly_plan_ids:
            monthly._onchange_year_month()

        self.state = 'confirm'
    

class MiningPlanMonth(models.Model):
    _name = 'mining.plan.month'
    _description = 'Mining Plan Month'

    @api.depends('sequence', 'year', 'work_days')
    def _compute_name(self):
        for record in self:
            record.name = MONTH_NAMES[record.sequence]
            year = record.year and record.year.year or 0
            record.work_days = monthrange(year, record.sequence + 1)[1]
            total_work_days = sum([monthrange(year, i)[1] for i in range(1, 13)])

    name = fields.Selection(
        selection=[(m, _(m.title())) for m in MONTH_NAMES],
        required=True,
        compute=_compute_name)

    sequence = fields.Integer(required=True)
    year = fields.Date(required=True, string='Year')

    plan_id = fields.Many2one(
        comodel_name='mining.plan', 
        required=True,
        ondelete='cascade',
        string='Mining Plan')

    work_days = fields.Integer(string='Work Days', compute=_compute_name)
    adjusted_monthly_target = fields.Float(string='Adjusted Monthly Target', digits='Product Unit of Measure', readonly=True)

    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        readonly=True)

    initial_monthly_target = fields.Float(
        string='Initial Monthly Target',
        digits='Product Unit of Measure',
        readonly=True)

    @api.onchange('initial_monthly_target')
    def _onchange_initial_monthly_target(self):
        self.adjusted_monthly_target = self.initial_monthly_target

    @api.constrains('work_days')
    def _constraints_work_days(self):
        for record in self:
            if not record.year:
                continue
            year = record.year.year
            max_days = monthrange(year, record.sequence + 1)[1]
            if record.work_days > max_days:
                month_name = MONTH_NAMES[record.sequence]
                raise UserError(_('The work days on %s is %s while %s %s only has %s days!'
                % (month_name, record.work_days, month_name, year, max_days)))


class MiningBudgetPlanning(models.Model):
    _name = 'mining.budget.planning'
    _description = 'Budget Planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def name_get(self):
        values = []
        for record in self:
            values += [(record.id, '%s - %s' % (record.estate_id.mining_site, record.year))]
        return values

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.onchange('year')
    def _onchange_year(self):
        self.month_ids.update({'year': self.year})

    @api.model
    def create(self, vals):
        result = super(MiningBudgetPlanning, self).create(vals)
        check_existing_budget_plannings = self.sudo().search([('estate_id', '=', result.estate_id.id), ('id', '!=', result.id)], limit=1)
        for budget_planning in check_existing_budget_plannings:
            if budget_planning.year.year == result.year.year:
                raise UserError(_("There is an existing Budget Plan for %s on year %s.") % (str(result.estate_id.mining_site), str(result.year.year)))
        return result

    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    estate_id = fields.Many2one('mining.site.control', string='Mining Site', required=True, tracking=True)

    year = fields.Date(
        string='Year',
        default=lambda self: fields.Date.today(),
        required=True,
        tracking=True)

    user_id = fields.Many2one('res.users', string='Responsible', required=True, default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, required=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True)
    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)

    month_ids = fields.One2many(
        comodel_name='mining.operations',
        inverse_name='plan_id',
        string='Monthly Target')