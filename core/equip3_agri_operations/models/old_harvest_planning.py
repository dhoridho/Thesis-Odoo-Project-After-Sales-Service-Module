import datetime
from locale import currency
from odoo import models, fields, api, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class HarvestPlanning(models.Model):
    _name = 'agriculture.harvest.planning'
    _description = 'Harvest Planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def name_get(self):
        values = []
        for record in self:
            values += [(record.id, '%s - %s' % (record.estate_id.name, record.year))]
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

    @api.model
    def _get_year_selection(self):
        now = datetime.datetime.now().year
        selection = []
        for year in range(now - 20, now + 6):
            selection += [(str(year), str(year))]
        return selection

    @api.depends('month_ids', 'month_ids.total')
    def _compute_total(self):
        for record in self:
            record.total = sum(record.month_ids.mapped('total'))

    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True, tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, tracking=True)
   
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
        comodel_name='agriculture.harvest.planning.month',
        inverse_name='plan_id',
        string='Monthly Target')

    total = fields.Float(string='Total', compute=_compute_total, store=True)

    @api.onchange('year')
    def _onchange_year(self):
        self.month_ids.update({'year': self.year})

    @api.onchange('estate_id')
    def _onchange_estate_id(self):
        division_ids = []
        if self.estate_id:
            division_ids = self.estate_id.division_ids
        division_id = False
        if division_ids:
            division_id = division_ids[0].id
        self.month_ids.update({'division_id': division_id})


class HarvestPlanningMonth(models.Model):
    _name = 'agriculture.harvest.planning.month'
    _description = 'Harvest PLanning Month'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        result = super(HarvestPlanningMonth, self).fields_get(allfields=allfields, attributes=attributes)
        for key in result.keys():
            if key in ('division_id', 'area'):
                continue
            result[key]['sortable'] = False
        return result

    @api.depends('val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep', 'val_oct', 'val_nov', 'val_dec')
    def _compute_total(self):
        for record in self:
            record.total = sum([record[key] for key in ['val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep', 'val_oct', 'val_nov', 'val_dec']])

    @api.depends('plan_id.year')
    def _compute_year(self):
        self.year = self.plan_id.year

    @api.depends('plan_id', 'plan_id.estate_id', 'plan_id.month_ids', 'plan_id.month_ids.division_id')
    def _compute_allowed_divisions(self):
        for record in self:
            allowed_division_ids = []
            added_division_ids = []
            if record.plan_id:
                added_division_ids = record.plan_id.month_ids.mapped('division_id').ids
                if record.plan_id.estate_id:
                    allowed_division_ids = record.plan_id.estate_id.division_ids.ids
            allowed_division_ids = list(set(allowed_division_ids) - set(added_division_ids))
            record.allowed_division_ids = [(6, 0, allowed_division_ids)]

    plan_id = fields.Many2one('agriculture.harvest.planning', string='Harvest Planning', required=True, ondelete='cascade')
    
    allowed_division_ids = fields.Many2many('agriculture.division', compute=_compute_allowed_divisions)
    division_id = fields.Many2one('agriculture.division', string='Division', required=True, domain="[('id', 'in', allowed_division_ids)]")

    area = fields.Float(string='Area')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    year = fields.Char(required=True, compute="_compute_year")

    company_id = fields.Many2one('res.company', related='plan_id.company_id')

    val_jan = fields.Float(string='January')
    val_feb = fields.Float(string='February')
    val_mar = fields.Float(string='March')
    val_apr = fields.Float(string='April')
    val_may = fields.Float(string='May')
    val_jun = fields.Float(string='June')
    val_jul = fields.Float(string='July')
    val_aug = fields.Float(string='August')
    val_sep = fields.Float(string='September')
    val_oct = fields.Float(string='October')
    val_nov = fields.Float(string='November')
    val_dec = fields.Float(string='December')

    total = fields.Float(string='Total', compute=_compute_total, store=True)

    @api.onchange('division_id')
    def _onchange_division_id(self):
        if self.division_id:
            self.area = self.division_id.area
            self.uom_id = self.division_id.area_uom_id
