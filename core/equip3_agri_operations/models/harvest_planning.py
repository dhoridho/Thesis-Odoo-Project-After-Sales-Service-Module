import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AnnualHarvestPlanning(models.Model):
    _name = 'annual.harvest.planning'
    _description = 'Annual Harvest Planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, readonly=True, default=_('New'))
    plan_name = fields.Char(required=True, tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    estate_id = fields.Many2one('crop.estate', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    year = fields.Date(required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    branch_id = fields.Many2one('res.branch', required=True, domain="[('company_id', '=', company_id)]", readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    target_ids = fields.One2many('annual.harvest.planning.target', 'annual_id', readonly=True, states={'draft': [('readonly', False)]}, string='Target')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm')
    ], default='draft', required=True)

    monthly_ids = fields.One2many('monthly.harvest.planning', 'annual_id')
    next_sequence = fields.Integer(compute='_compute_next_sequence')
    is_monthly_planning = fields.Boolean(related='company_id.agriculture_monthly_planning')

    _sql_constraints = [
        ('unique_year_estate', 'unique(year,estate_id)', 'Annual Harvest Planning for choosed estate & year already created. Please choose another estate/year.')
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('annual.harvest.planning') or _('New')
        return super(AnnualHarvestPlanning, self).create(vals)

    @api.depends('target_ids')
    def _compute_next_sequence(self):
        for record in self:
            record.next_sequence = len(record.target_ids) + 1

    def _prepare_monthly_values(self):
        self.ensure_one()
        static_value = {
            'annual_id': self.id,
            'estate_id': self.estate_id.id,
            'year': self.year,
            'branch_id': self.branch_id.id,
            'company_id': self.company_id.id,
            'target_ids': [(0, 0, {
                'sequence': target.sequence,
                'division_id': target.division_id.id,
                'block_id': target.block_id.id,
                'quantity': target.quantity / 12
            }) for target in self.target_ids]
        }
        year = self.year.year
        values = []
        for month in range(1, 13):
            value = static_value.copy()
            value['month'] =  datetime.date(year, month, 1)
            values += [value]
        return values

    def action_confirm(self):
        self.ensure_one()
        if self.is_monthly_planning:
            monthly_vals = self._prepare_monthly_values()
            self.env['monthly.harvest.planning'].create(monthly_vals)
        self.state = 'confirm'

    def action_view_monthly_planning(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('equip3_agri_operations.action_view_monthly_harvest_planning')
        records = self.monthly_ids
        if not records:
            return
        if len(records) > 1:
            action['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('equip3_agri_operations.view_monthly_harvest_planning_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(s, v) for s, v in action['views'] if v != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = records.id
        action['context'] = str(dict(eval(action.get('context') or '{}', self._context), create=False))
        return action

    @api.onchange('estate_id')
    def _onchange_estate_id(self):
        self.target_ids.update({
            'estate_id': self.estate_id.id,
            'division_id': False,
            'block_id': False
        })


class AnnualHarvestPlanningTarget(models.Model):
    _name = 'annual.harvest.planning.target'
    _description = 'Annual Harvest Planning Target'

    annual_id = fields.Many2one('annual.harvest.planning', required=True, ondelete='cascade')
    estate_id = fields.Many2one('crop.estate', required=True)
    sequence = fields.Integer(string='No')
    division_id = fields.Many2one('agriculture.division', required=True, domain="[('estate_id', '=', estate_id)]")
    block_id = fields.Many2one('crop.block', required=True, domain="[('estate_id', '=', estate_id), ('division_id', '=', division_id)]")
    quantity = fields.Float(string='Target Quantity', default=1.0)

    @api.onchange('division_id')
    def _onchange_division_id(self):
        self.block_id = False

    _sql_constraints = [
        ('unique_divblock', 'unique(annual_id,division_id,block_id)', 'Target for choosed division & block already created. Please choose another division/block.'),
        ('check_quantity', 'CHECK(quantity > 0.0)', 'Target Quantity must be positive!')
    ]


class MonthlyHarvestPlanning(models.Model):
    _name = 'monthly.harvest.planning'
    _description = 'Monthly Harvest Planning'

    annual_id = fields.Many2one('annual.harvest.planning', required=True, ondelete='cascade', string='Plan Reference')
    name = fields.Char(required=True, readonly=True, default=_('New'))
    estate_id = fields.Many2one('crop.estate', required=True)
    year = fields.Date(required=True)
    month = fields.Date(required=True)
    branch_id = fields.Many2one('res.branch', required=True, domain="[('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    target_ids = fields.One2many('monthly.harvest.planning.target', 'monthly_id', string='Target')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('monthly.harvest.planning') or _('New')
        return super(MonthlyHarvestPlanning, self).create(vals)


class MonthlyHarvestPlanningTarget(models.Model):
    _name = 'monthly.harvest.planning.target'
    _description = 'Monthly Harvest Planning Target'

    monthly_id = fields.Many2one('monthly.harvest.planning', required=True, ondelete='cascade')
    estate_id = fields.Many2one(related='monthly_id.estate_id')
    sequence = fields.Integer(string='No')
    division_id = fields.Many2one('agriculture.division', required=True, domain="[('estate_id', '=', estate_id)]")
    block_id = fields.Many2one('crop.block', required=True, domain="[('estate_id', '=', estate_id), ('division_id', '=', division_id)]")
    quantity = fields.Float(string='Target Quantity', default=1.0)

    @api.onchange('division_id')
    def _onchange_division_id(self):
        self.block_id = False

    _sql_constraints = [
        ('unique_divblock', 'unique(monthly_id,division_id,block_id)', 'Target for choosed division & block already created. Please choose another division/block.'),
        ('check_quantity', 'CHECK(quantity > 0.0)', 'Target Quantity must be positive!')
    ]
