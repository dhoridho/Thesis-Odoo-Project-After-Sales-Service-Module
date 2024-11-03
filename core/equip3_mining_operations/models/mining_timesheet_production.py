from odoo import models, fields, api, _


class MiningTimesheetProduction(models.Model):
    _name = 'mining.timesheet.production'
    _description = 'Mining Timesheet Production'

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('New')) == _('New'):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('mining.timesheet.production', sequence_date=None) or _('New')
            vals['name'] = vals['sequence']

        return super(MiningTimesheetProduction, self).create(vals)

    @api.depends('timesheet_record_ids.end_time')
    def _compute_end_date(self):
        if len(self.timesheet_record_ids) > 1:
            if self.end_date != self.timesheet_record_ids[-1].end_time:
                if self.end_date:
                    self.timesheet_record_ids[-1].start_time = self.end_date

        elif len(self.timesheet_record_ids) == 1:
            self.timesheet_record_ids[-1].start_time = self.start_date

        last_timesheet = self.timesheet_record_ids.mapped('end_time')
        last_time = None
        for etime in last_timesheet:
            last_time = etime

        self.end_date = last_time

    @api.onchange('company_id', 'branch_id')
    def _onchange_company_id(self):
        company_id = self.company_id.id
        branch_id = self.branch_id.id
        self.mining_site_id = self.env['mining.site.control'].search([
            ('company_id', '=', company_id), ('branch_id', '=', branch_id)
        ], limit=1).id

    sequence = fields.Char(required=True, copy=False, readonly=True, default=_('New'), tracking=True, string='Reference')

    name = fields.Char(string="Name", readonly=True, states={'draft': [('readonly', False)]})

    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site', required=True, readonly=True, states={'draft': [('readonly', False)]})

    allowed_operation_ids = fields.Many2many(comodel_name='mining.operations')
    allowed_operation_two_ids = fields.Many2many(comodel_name='mining.operations.two')
    operation_id = fields.Many2one(comodel_name='mining.operations', string='Operation',
        domain="[('id', 'in', allowed_operation_ids)]", readonly=True, states={'draft': [('readonly', False)]})

    mining_operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation',
        domain="[('id', 'in', allowed_operation_two_ids)]", required=True, readonly=True, states={'draft': [('readonly', False)]})
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment', required=True, readonly=True, states={'draft': [('readonly', False)]})

    start_date = fields.Datetime(string="Start Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Datetime(string="End Date", readonly=True, compute='_compute_end_date', store=True)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, readonly=True, states={'draft': [('readonly', False)]})
    create_uid = fields.Many2one(comodel_name='res.users', string='Created By', default=lambda self: self.env.user, readonly=True, states={'draft': [('readonly', False)]})

    timesheet_record_ids = fields.One2many('mining.timesheet.production.timesheet', 'timesheet_production_id', string='Time Sheet', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm')
        ], string='Status', readonly=True, default='draft'
    )

    equipment_vehicle_checkbox = fields.Boolean(related='equipment_id.vehicle_checkbox')

    last_odometer = fields.Float(string='Last Odometer', readonly=True)
    last_hourmeter  = fields.Float(string='Last Hour Meter', readonly=True)
    odometer = fields.Float(string='Odoometer', readonly=True, states={'draft': [('readonly', False)]})
    hourmeter = fields.Float(string='Hour Meter', readonly=True, states={'draft': [('readonly', False)]})

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        is_vehicle = self.equipment_id.vehicle_checkbox if self.equipment_id else False
        last_odometer = 0.0
        if is_vehicle:
            last_odometer = self.env['maintenance.vehicle'].search(
                [('maintenance_vehicle', '=', self.equipment_id.id)], order='date,id desc', limit=1).value
        last_hourmeter = self.env['maintenance.hour.meter'].search(
            [('maintenance_asset', '=', self.equipment_id.id)], order='date,id desc', limit=1).value
        self.last_hourmeter = last_hourmeter
        self.last_odometer = last_odometer

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

    def action_confirm(self):
        self.ensure_one()
        today = fields.Date.today()
        is_vehicle = self.equipment_id.vehicle_checkbox if self.equipment_id else False

        if is_vehicle:
            self.env['maintenance.vehicle'].create({
                'date': today,
                'maintenance_vehicle': self.equipment_id.id,
                'value': self.odometer
            })
        self.env['maintenance.hour.meter'].create({
            'date': today,
            'maintenance_asset': self.equipment_id.id,
            'value': self.hourmeter
        })
        self.state = 'confirm'


class MiningTimesheetProductionTimesheet(models.Model):
    _name = 'mining.timesheet.production.timesheet'
    _description = 'Mining Timesheet Production Timesheet'

    timesheet_production_id = fields.Many2one('mining.timesheet.production', ondelete='cascade')

    start_time_tmp = fields.Datetime(string="Start Time Tmp", related='timesheet_production_id.end_date')
    start_time = fields.Datetime(string="Start Time", required=True, readonly=True)
    end_time = fields.Datetime(string="End Time", required=True)
    operator_id = fields.Many2one(comodel_name='res.users', string='Operator', default=lambda self: self.env.user)
    activity_type = fields.Selection(
        selection=[
            ('operative', 'Operative'),
            ('idle', 'Idle'),
            ('breakdown', 'Breakdown')
        ],
        string='Activity Type',
        required=True
    )
    activity_id = fields.Many2one('mining.timesheet.activity', string="Activity")
    notes = fields.Text(string='Notes')

    @api.onchange('activity_type')
    def _onchange_activity_type(self):
        self.activity_id = self.env['mining.timesheet.activity'].search([
            ('activity_type', '=', self.activity_type)
        ], limit=1).id
