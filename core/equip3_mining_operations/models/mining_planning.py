import calendar
from datetime import datetime

from odoo import models, fields, api, _

class MiningPlanning(models.Model):
    _name = 'mining.planning'
    _description = 'Mining Planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('New')) == _('New'):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('mining.planning', sequence_date=None) or _('New')
        return super(MiningPlanning, self).create(vals)

    def write(self, vals):
        res = super(MiningPlanning, self).write(vals)
        for record in self:
            if record.annual_month_id:
                record.annual_month_id.write({'adjusted_monthly_target': record.adjusted_target})
        return res

    @api.model
    def _default_filter_year(self):
        return fields.Date.today().replace(day=1, month=1)

    @api.onchange('company_id', 'branch_id')
    def _onchange_company_id(self):
        company_id = self.company_id.id
        branch_id = self.branch_id.id
        self.mining_site_id = self.env['mining.site.control'].search([
            ('company_id', '=', company_id), ('branch_id', '=', branch_id)
        ], limit=1).id

    @api.depends('production_ids', 'production_ids.adjusted_target')
    def _compute_adjusted_target(self):
        for record in self:
            record.adjusted_target = sum(record.production_ids.mapped('adjusted_target'))

    sequence = fields.Char(required=True, copy=False, readonly=True, default=_('New'), tracking=True, string='Reference')

    name = fields.Char(required=True, tracking=True)

    month = fields.Selection(selection=[
        ('january', _('January')),
        ('february', _('February')),
        ('march', _('March')),
        ('april', _('April')),
        ('may', _('May')),
        ('june', _('June')),
        ('july', _('July')),
        ('august', _('August')),
        ('september', _('September')),
        ('october', _('October')),
        ('november', _('November')),
        ('december', _('December')),
    ], required=True, string='Month')

    mining_site_id = fields.Many2one(
        comodel_name='mining.site.control',
        string='Mining Site',
        required=True,
        tracking=True)
    
    mining_pit_id = fields.Many2one(
        comodel_name='mining.project.control',
        string='Mining Pit',
        required=False,
        tracking=True)

    allowed_operation_ids = fields.Many2many(
        comodel_name='mining.operations')

    allowed_operation_two_ids = fields.Many2many(
        comodel_name='mining.operations.two')

    operation_id = fields.Many2one(
        comodel_name='mining.operations',
        string='Operation',
        domain="[('id', 'in', allowed_operation_ids)]",
        tracking=True)

    mining_operation_id = fields.Many2one(
        comodel_name='mining.operations.two',
        string='Operation',
        domain="[('id', 'in', allowed_operation_two_ids)]",
        required=True,
        tracking=True)

    year_month = fields.Date(
        string='Month',
        default=lambda self: fields.Date.today(),
        required=True,
        readonly=True)

    company_id = fields.Many2one(
        comodel_name='res.company', 
        string='Company', 
        default=lambda self: self.env.company, 
        readonly=True, 
        required=True)

    branch_id = fields.Many2one(
        comodel_name='res.branch',
        string='Branch', required=True, tracking=True)

    create_uid = fields.Many2one(
        comodel_name='res.users', 
        string='Created By', 
        default=lambda self: self.env.user, 
        tracking=True)

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        readonly=True
    )

    uom_id = fields.Many2one(
        comodel_name='uom.uom', 
        string='Unit of Measure', 
        readonly=True)

    initial_target = fields.Float(
        string='Initial Target', 
        digits='Product Unit of Measure',
        readonly=True)

    initial_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Initial UoM',
        readonly=True)

    adjusted_target = fields.Float(
        string='Adjusted Target', 
        digits='Product Unit of Measure',
        compute=_compute_adjusted_target)

    adjusted_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Adjusted UoM',
        readonly=True)

    production_ids = fields.One2many('mining.planning.production', 'mining_planning_id', string='Production')

    # technical fields
    annual_id = fields.Many2one('mining.plan', string='Annual Plan')
    annual_month_id = fields.Many2one('mining.plan.month', string='Annual Plan Month')

    @api.onchange('mining_site_id', 'allowed_operation_two_ids')
    def _onchange_mining_site_id(self):
        shelter = []
        self.allowed_operation_two_ids = None
        self.mining_operation_id = None
        if self.mining_site_id:
            shelter = self.mining_site_id.operation_ids.ids
            self.allowed_operation_two_ids = [(6, 0, shelter)]
            if len(shelter) > 0:
                self.mining_operation_id = shelter[0]

    @api.onchange('year_month', 'initial_target')
    def _onchange_year_month(self):
        if self.year_month:
            year = self.year_month.year
            month = self.year_month.month
            num_days = calendar.monthrange(year, month)[1]

            day_list = [datetime(year, month, day) for day in range(1, num_days+1)]
            day_strings = [day.strftime("%Y-%m-%d") for day in day_list]
            target_qty = self.initial_target / num_days

            self.production_ids = [(5,)] + [(0, 0, {
                'production_date': day_string,
                'initial_target': target_qty,
                'adjusted_target': target_qty
            }) for day_string in day_strings]

    @api.onchange('mining_operation_id')
    def _onchange_mining_operation_id(self):
        uom_id = self.mining_operation_id and self.mining_operation_id.uom_id.id or False
        self.initial_uom_id = uom_id
        self.adjusted_uom_id = uom_id


class MiningPlanMonth(models.Model):
    _name = 'mining.planning.production'
    _description = 'Mining Planning Production'

    mining_planning_id = fields.Many2one('mining.planning')
    production_date = fields.Date("Date", readonly=True)
    initial_target = fields.Float(digits='Product Unit of Measure', string='Initial Target', readonly=True)
    adjusted_target = fields.Float(digits='Product Unit of Measure', string='Adjusted Target')


