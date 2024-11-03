import datetime
from odoo import models, fields, api, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class BudgetPlanningBlock(models.Model):
    _name = 'agriculture.budget.planning.block'
    _description = 'Budget Planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def name_get(self):
        values = []
        for record in self:
            values += [(record.id, '%s - %s' % (record.division_id.name, record.year))]
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

    @api.depends('month_ids')
    def _compute_allowed_block_selection(self):
        for rec in self:
            allowed =[]
            for i in rec.month_ids.block_id:
                allowed.append(i.id)
            rec.allowed_block_ids = [(6, 0, allowed)]
        
    @api.model
    def _default_month_ids(self, division_id=None):
        domain = []
        if division_id is not None:
            domain = [('division_id', '=', division_id)]
        month_values = []
        for block in self.env['crop.block'].search(domain):
            month_values.append([0, 0, {'block_id': block.id}])
        return month_values

    @api.model
    def _get_year_selection(self):
        now = datetime.datetime.now().year
        selection = []
        for year in range(now - 20, now + 6):
            selection += [(str(year), str(year))]
        return selection

    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True, tracking=True)
    division_id = fields.Many2one('agriculture.division', string='Division', required=True, tracking=True)

    year = fields.Selection(
        selection=_get_year_selection,
        required=True,
        default=lambda self: str(datetime.datetime.now().year),
        string='Year',
        tracking=True)

    user_id = fields.Many2one('res.users', string='Responsible', required=True, default=lambda self: self.env.user, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, required=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True)
    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)

    month_ids = fields.One2many(
        comodel_name='agriculture.budget.planning.block.month',
        inverse_name='plan_id',
        string='Monthly Target',
        default=_default_month_ids)
  
    allowed_block_ids = fields.One2many('crop.block', compute=_compute_allowed_block_selection)

    @api.onchange('year')
    def _onchange_year(self):
        self.month_ids.update({'year': self.year})

    @api.onchange('division_id')
    def _onchange_division_id(self):
        month_values = [(5,)] + self._default_month_ids(division_id=self.division_id.id)
        self.month_ids = month_values

    _sql_constraints = [
        ('unique_year', 'Check(1=1)', 'Planning for the selected year already exists, please check!'),
        (
            "unique_budget_planning",
            "unique(estate_id, division_id, year)",
            "Planning for the selected year already exists, please check!",
        )
    ]


class BudgetPlanningBlockMonth(models.Model):
    _name = 'agriculture.budget.planning.block.month'
    _description = 'Budget Planning Month'
    _rec_name = 'block_id'

    @api.depends('val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep', 'val_oct', 'val_nov', 'val_dec')
    def _compute_total(self):
        for record in self:
            record.total = sum([record[key] for key in ['val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep', 'val_oct', 'val_nov', 'val_dec']])

    @api.depends('plan_id.year')
    def _compute_year(self):
        self.year = self.plan_id.year

    @api.depends('block_id')
    def _compute_from_block(self):
        for record in self:
            tt = False
            ha = 0.0
            pkk = 0.0
            sph = 0.0
            if record.block_id:
                tt = record.block_id.crop_ids and min(record.block_id.crop_ids.mapped('crop_date')) or False
                ha = record.block_id.size
                pkk = sum(record.block_id.crop_ids.mapped('crop_count'))
                sph = ha / pkk if pkk > 0.0 else 0.0
            record.tt = tt
            record.ha = ha
            record.pkk = pkk
            record.sph = sph 

    plan_id = fields.Many2one('agriculture.budget.planning.block', string='Budget Planning', required=True, ondelete='cascade')
    
    division_id = fields.Many2one('agriculture.division', related='plan_id.division_id')
    block_id = fields.Many2one('crop.block', string='Block')

    @api.onchange('block_id')
    def block_id_change(self):
        allowed_list = [x.id for x in self.plan_id.allowed_block_ids]
        return {'domain': {'block_id': [('division_id', '=', self.division_id.id), ('id', 'not in', allowed_list)]}}

    tt = fields.Date(string='TT', compute=_compute_from_block, store=True)
    ha = fields.Float(string='HA', compute=_compute_from_block, store=True)
    pkk = fields.Float(string='PKK', compute=_compute_from_block, store=True)
    sph = fields.Float(string='SPH', compute=_compute_from_block, store=True)

    year = fields.Char(required=True, compute="_compute_year")

    company_id = fields.Many2one('res.company', related='plan_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    val_jan = fields.Monetary(string='January')
    val_feb = fields.Monetary(string='February')
    val_mar = fields.Monetary(string='March')
    val_apr = fields.Monetary(string='April')
    val_may = fields.Monetary(string='May')
    val_jun = fields.Monetary(string='June')
    val_jul = fields.Monetary(string='July')
    val_aug = fields.Monetary(string='August')
    val_sep = fields.Monetary(string='September')
    val_oct = fields.Monetary(string='October')
    val_nov = fields.Monetary(string='November')
    val_dec = fields.Monetary(string='December')

    total = fields.Monetary(string='Total', compute=_compute_total, store=True)