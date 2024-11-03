from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import ValidationError


class PlantationLines(models.Model):
    _name = 'agriculture.daily.activity.line'
    _description = 'Plantation Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _register_hook(self):
        super(PlantationLines, self)._register_hook()
        self._update_daily_activity_type()

    @api.model
    def _update_daily_activity_type(self):
        to_update = self.sudo().search([('daily_activity_type', '=', 'daily_activity')])
        to_update.write({'daily_activity_type': 'plantation'})

    @api.model
    def create(self, vals):
        # if record created from daily.activity.line form, then create reference sequence
        # else, reference sequence created when activity.line confirmed
        if vals.get('name', _('New')) == _('New') and 'daily_activity_id' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.daily.activity.line') or _('New')

        agreement_id = vals.get('agreement_id', False)
        if agreement_id:
            agreement = self.env['agri.agreement'].browse(agreement_id)
            vals['agreement_sequence'] = len(agreement.activity_line_ids) + 1
        return super(PlantationLines, self).create(vals)

    def write(self, vals):
        # if record has daily_activity_id and record is confirmed, then create reference sequence
        if vals.get('state') == 'confirm' and vals.get('daily_activity_id', self.daily_activity_id):
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.daily.activity.line') or _('New')
        return super(PlantationLines, self).write(vals)

    def name_get(self):
        values = []
        for record in self:
            name = record.name
            if name == _('New'):
                name = '%s - %s' % (name, record.activity_id.display_name)
            values.append((record.id, name))
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
    def _default_analytic_tag_ids(self, force_company=False, force_branch=False):
        if self.env.context.get('analytic_group_ids', False):
            return self.env.context.get('analytic_group_ids')
        company_id = self.env['res.company'].browse(force_company or self.env.context.get('default_company_id', self.env.company.id))
        branch_id = self.env['res.branch'].browse(force_branch or self._default_branch())
        if company_id and branch_id:
            analytic_priority_ids = self.env['analytic.priority'].search([], order='priority')
            for analytic_priority in analytic_priority_ids:
                if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                    analytic_tags_ids = self.env['account.analytic.tag'].search([
                        ('id', 'in', self.env.user.analytic_tag_ids.ids),
                        ('company_id', '=', company_id.id)
                    ])
                    return [(6, 0, analytic_tags_ids.ids)]
                elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                    analytic_tags_ids = self.env['account.analytic.tag'].search([
                        ('id', 'in', branch_id.analytic_tag_ids.ids),
                        ('company_id', '=', company_id.id)
                    ])
                    self.analytic_group_ids = analytic_tags_ids
                    return [(6, 0, analytic_tags_ids.ids)]
        return False

    @api.depends('date_scheduled')
    def _compute_date_scheduled_end(self):
        for record in self:
            record.date_scheduled_end = record.date_scheduled + relativedelta(days=1)

    @api.depends('date_scheduled')
    def _compute_datetime_scheduled(self):
        for record in self:
            record.datetime_scheduled = fields.Datetime.to_datetime(record.date_scheduled)

    @api.depends('company_id')
    def _compute_production_location(self):
        location_by_company = self.env['stock.location'].read_group([
            ('company_id', 'in', self.company_id.ids),
            ('usage', '=', 'production')
        ], ['company_id', 'ids:array_agg(id)'], ['company_id'])
        location_by_company = {lbc['company_id'][0]: lbc['ids'] for lbc in location_by_company}
        for record in self:
            record.production_location_id = location_by_company.get(record.company_id.id)[0]

    @api.depends('location_id')
    def _compute_warehouse(self):
        for record in self:
            record.warehouse_id = False
            if record.location_id:
                record.warehouse_id = record.location_id.get_warehouse().id

    def _compute_all_moves_done(self):
        for record in self:
            moves = record.material_ids | record.harvest_ids
            record.all_moves_done = all(state in ('done', 'cancel') for state in moves.mapped('state'))
    
    @api.depends('crop_ids', 'crop_ids.crop_date')
    def _compute_crop_age(self):
        for record in self:
            crop_age = False
            crop_dates = record.crop_ids.mapped('crop_date')
            if crop_dates:
                oldest_date = min(crop_dates)
                if oldest_date:
                    delta = relativedelta(fields.Date.today(), oldest_date)
                    if delta.years < 4:
                        crop_age = 'TBM'
                    else:
                        crop_age = 'TM'
            record.crop_age = crop_age

    def _compute_planting_moves_count(self):
        for record in self:
            moves = record.planting_move_ids | record.material_ids
            record.planting_moves_count = len(moves.filtered(lambda m: m.state == 'done'))

    def _compute_moves(self):
        for record in self:
            moves = record.material_ids | record.harvest_ids
            if record.activity_harvest_type == 'logging':
                moves |= record.crop_move_ids
            record.moves_count = len(moves.filtered(lambda m: m.state == 'done'))

    @api.depends('block_id')
    def _compute_allowed_sub_blocks(self):
        for record in self:
            record.allowed_sub_block_ids = [(6, 0, record.block_id.sub_ids.filtered(lambda o: o.state == 'active').ids)]

    @api.model
    def _default_picking_type(self):
        return self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1).id

    daily_activity_type = fields.Selection(
        selection=[('daily_activity', 'Daily Activity'), ('plantation', 'Plantation')], default='plantation', string='Operation Type', required=True)

    sequence = fields.Integer()
    agreement_sequence = fields.Integer()

    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan', readonly=True)
    is_matrix_on = fields.Boolean(related='daily_activity_id.is_matrix_on')
    
    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    
    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    category_type = fields.Char(related='activity_id.category_type')
    activity_type = fields.Char(related='activity_id.activity_type')
    activity_harvest_type = fields.Char(related='activity_id.harvest_type')

    worker_group_ids = fields.One2many('agriculture.daily.activity.worker', 'activity_line_id', string='Worker Group')
    
    notes = fields.Text(string='Notes', tracking=True, readonly=True, states={'draft': [('readonly', False)]})

    date_scheduled = fields.Date(string='Scheduled Date', required=True, default=fields.Date.today, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    date_scheduled_end = fields.Date(string='Scheduled Date End', compute=_compute_date_scheduled_end)
    
    block_id = fields.Many2one('crop.block', string='Block', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-block', readonly=True, states={'draft': [('readonly', False)]}, domain="[('id', 'in', allowed_sub_block_ids)]", tracking=True)
    allowed_sub_block_ids = fields.Many2many('crop.block.sub', compute='_compute_allowed_sub_blocks')
    
    block_size = fields.Float(related='block_id.size')
    block_uom_id = fields.Many2one(related='block_id.uom_id')

    crop_ids = fields.Many2many('agriculture.crop', string='Crop', readonly=True)

    analytic_group_ids = fields.Many2many('account.analytic.tag', domain="[('company_id', '=', company_id)]", string="Analytic Group", readonly=True, states={'draft': [('readonly', False)]}, default=_default_analytic_tag_ids)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, required=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    
    create_uid = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    
    harvest_ids = fields.One2many('stock.move', 'activity_line_harvest_id', string='Harvest')
    material_ids = fields.One2many('stock.move', 'activity_line_material_id', string='Materials')
    asset_ids = fields.One2many('agriculture.daily.activity.asset', 'activity_line_id', string='Assets')
    activity_record_ids = fields.One2many('agriculture.daily.activity.record', 'activity_line_id', string='Activity Records', readonly=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('paid', 'Paid')
    ], string='Status', default='draft', tracking=True)

    estate_id = fields.Many2one('crop.estate', related='block_id.estate_id')
    location_id = fields.Many2one('stock.location', string='Location', related='block_id.location_id')
    production_location_id = fields.Many2one('stock.location', string='Production Location', compute=_compute_production_location)
    datetime_scheduled = fields.Datetime(compute=_compute_datetime_scheduled)
    warehouse_id = fields.Many2one('stock.warehouse', compute=_compute_warehouse)

    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')
    state_3 = fields.Selection(related='state', tracking=False, string='State 3')
    all_moves_done = fields.Boolean(compute=_compute_all_moves_done)

    harvest = fields.Boolean(string='Harvest')
    nursery = fields.Boolean(string='Nursery')
    nursery_ids = fields.One2many('agriculture.daily.activity.nursery', 'activity_line_id', string='Nursery')

    crop_age = fields.Selection(
        selection=[
            ('TBM', 'TBM'),
            ('TM', 'TM')
        ],
        string='Crop Age',
        tracking=True,
        readonly=False,
        compute=_compute_crop_age,
        store=True
    )

    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'activity_line_id', readonly=True)
    worker_type = fields.Selection(selection=[
        ('with_group', 'With Group'),
        ('without_group', 'Without Group')
    ], default='with_group', readonly=True, states={'draft': [('readonly', False)]})

    is_whole_day = fields.Boolean(readonly=True, states={'draft': [('readonly', False)]})
    start_time = fields.Datetime(readonly=True, states={'draft': [('readonly', False)]})
    end_time = fields.Datetime(readonly=True, states={'draft': [('readonly', False)]})

    planting_move_ids = fields.One2many('stock.move', 'activity_line_planting_id', string='Planting Moves')
    planting_moves_count = fields.Integer(compute=_compute_planting_moves_count)
    moves_count = fields.Integer(compute=_compute_moves)

    agreement_id = fields.Many2one('agri.agreement', string='Agreement', domain="[('agreement_type', '=', daily_activity_type), ('state', '=', 'progress')]", readonly=True, states={'draft': [('readonly', False)]})

    picking_type_id = fields.Many2one('stock.picking.type', default=_default_picking_type)

    size = fields.Float(digits='Product Unit of Measure', string='Area Size', default=1.0, readonly=True, states={'draft': [('readonly', False)]})
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    def _get_material_values(self):
        self.ensure_one()
        material_vals = []
        for seq, line in enumerate(self.activity_id.material_ids):
            product_id = line.product_id
            material_vals += [{
                'daily_activity_material_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'activity_line_material_id': self.id,
                'activity_material_id': line.id,
                'sequence': seq,
                'name': self.name,
                'date': self.datetime_scheduled,
                'date_deadline': self.datetime_scheduled,
                'product_id': product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'quantity_done': line.quantity,
                'location_id': self.location_id.id,
                'location_dest_id': product_id.with_company(self.company_id).property_stock_production.id,
                'company_id': self.company_id.id,
                'price_unit': product_id.standard_price,
                'origin': self.name,
                'state': 'draft',
                'warehouse_id': self.location_id.get_warehouse().id,
                'picking_type_id': self.picking_type_id.id
            }]
        return material_vals

    def _get_harvest_values(self):
        self.ensure_one()
        harvest_vals = []
        for seq, harvest in enumerate(self.activity_id.harvest_ids):
            harvest_vals += [{
                'daily_activity_harvest_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'activity_line_harvest_id': self.id,
                'activity_harvest_id': harvest.id,
                'block_id': self.block_id.id,
                'sub_block_id': self.sub_block_id.id,
                'sequence': seq,
                'name': self.name,
                'date': fields.Datetime.to_datetime(self.date_scheduled),
                'date_deadline': fields.Datetime.to_datetime(self.date_scheduled),
                'product_id': harvest.product_id.id,
                'product_uom_qty': harvest.product_uom_qty,
                'product_uom': harvest.product_uom_id.id,
                'quantity_done': harvest.product_uom_qty,
                'location_id': harvest.product_id.with_company(self.company_id).property_stock_production.id,
                'location_dest_id': self.location_id.id,
                'company_id': self.company_id.id,
                'origin': self.name,
                'state': 'draft'
            }]
        return harvest_vals

    def _get_nursery_values(self):
        self.ensure_one()
        nursery_vals = []
        for seq, nursery in enumerate(self.activity_id.crop_ids):
            nursery_vals += [{
                'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'activity_line_id': self.id,
                'product_id': nursery.product_id.id,
                'block_id': self.block_id.id,
                'count': nursery.product_uom_qty,
                'date': self.date_scheduled,
                'uom_id': nursery.product_uom_id.id
            }]
        return nursery_vals

    def _get_asset_values(self):
        self.ensure_one()
        asset_vals = []
        for asset in self.activity_id.asset_ids:
            asset_vals += [{
                'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'activity_line_id': self.id,
                'activity_asset_id': asset.id,
                'asset_id': asset.asset_id.id,
                'user_id': asset.user_id.id,
                'original_move': True
            }]
        return asset_vals

    @api.onchange('harvest', 'block_id', 'sub_block_id')
    def _onchange_harvest(self):
        harvest_ids = [(5,)]
        if self.harvest:
            harvest_ids += [(0, 0, values) for values in self._get_harvest_values()]
        self.harvest_ids = harvest_ids

    @api.onchange('nursery')
    def _onchange_nursery(self):
        nursery_ids = [(5,)]
        if self.nursery:
            nursery_ids += [(0, 0, values) for values in self._get_nursery_values()]
        self.nursery_ids = nursery_ids

    @api.onchange('activity_id')
    def _onchange_activity_id(self):
        if not self.activity_id:
            return
        self.material_ids = [(5,)] + [(0, 0, values) for values in self._get_material_values()]
        self.asset_ids = [(5,)] + [(0, 0, values) for values in self._get_asset_values()]
        if self.activity_id.group_id and self.activity_id.group_id.category_id:
            self.harvest = self.activity_id.group_id.category_id.value == 'harvest'
            self.nursery = self.activity_id.group_id.category_id.value == 'nursery'

    @api.onchange('location_id')
    def _onchange_location_id(self):
        location_id = self.location_id
        if not location_id:
            return
        warehouse_id = location_id.get_warehouse()
        if self.material_ids:
            self.material_ids.update({
                'location_id': location_id.id,
                'warehouse_id': warehouse_id.id
            })
        if self.harvest_ids:
            self.harvest_ids.update({
                'location_dest_id': location_id.id,
                'warehouse_id': warehouse_id.id
            })

    @api.onchange('block_id')
    def _onchange_block_id(self):
        crop_ids = []
        if self.block_id:
            crop_ids = self.block_id.crop_ids.ids
            
        self.crop_ids = [(6, 0, crop_ids)]
        if self.nursery_ids:
            self.nursery_ids.update({'block_id': self.block_id.id})

        if not self.sub_block_id:
            self.size = self.env.context.get('default_size', self.block_id.size)
            self.uom_id = self.env.context.get('default_uom_id', self.block_id.uom_id.id)

    @api.onchange('sub_block_id')
    def _onchange_sub_block_id(self):
        if self.sub_block_id:
            self.size = self.sub_block_id.size
            self.uom_id = self.sub_block_id.uom_id.id

    @api.onchange('date_scheduled')
    def _onchange_date_scheduled(self):
        if self.nursery_ids:
            self.nursery_ids.update({'date': self.date_scheduled})

    @api.constrains('is_whole_day', 'start_time', 'end_time')
    def _check_start_end_time(self):
        for record in self:
            if not record.is_whole_day and record.start_time and record.end_time and record.start_time >= record.end_time:
                raise ValidationError(_('End Time cannot be earlier than Start Time!'))

    def _prepare_activity_record_vals(self):
        self.ensure_one()
        nursery_ids = self.nursery_ids.filtered(lambda n: not n.activity_record_id).ids
        if not nursery_ids and self.nursery_ids:
            nursery_ids = self.nursery_ids.filtered(lambda n: n.original_move)
            if nursery_ids:
                nursery_ids = nursery_ids.copy({'activity_record_id': False}).ids
            else:
                nursery_ids = []

        asset_ids = self.asset_ids.filtered(lambda a: not a.activity_record_id).ids
        if not asset_ids and self.asset_ids:
            asset_ids = self.asset_ids.filtered(lambda a: a.original_move)
            if asset_ids:
                asset_ids = asset_ids.copy({'activity_record_id': False}).ids
            else:
                asset_ids = []

        worker_group_ids = self.worker_group_ids.filtered(lambda w: not w.activity_record_id).ids
        if not worker_group_ids and self.worker_group_ids:
            worker_group_ids = self.worker_group_ids.filtered(lambda w: w.original_move)
            if worker_group_ids:
                worker_group_ids = worker_group_ids.copy({'activity_record_id': False}).ids
            else:
                worker_group_ids = []

        harvest_ids = self.harvest_ids.filtered(lambda m: m.state not in ('done', 'cancel')).ids
        material_ids = self.material_ids.filtered(lambda m: m.state not in ('done', 'cancel')).ids
        
        return {
            'daily_activity_type': self.daily_activity_type,
            'is_whole_day': self.is_whole_day,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'activity_line_id': self.id,
            'priority': self.priority,
            'activity_id': self.activity_id.id,
            'harvest': self.harvest,
            'nursery': self.nursery,
            'block_id': self.block_id.id,
            'sub_block_id': self.sub_block_id.id,
            'date_scheduled': self.date_scheduled,
            'date_scheduled_end': self.date_scheduled_end,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'crop_age': self.crop_age,
            'agreement_id': self.agreement_id.id,
            'picking_type_id': self.picking_type_id.id,
            'planned_size': self.size,
            'size': self.size,
            'uom_id': self.uom_id.id,
            'harvest_ids': [(6, 0, harvest_ids)],
            'material_ids': [(6, 0, material_ids)],
            'nursery_ids': [(6, 0, nursery_ids)],
            'asset_ids': [(6, 0, asset_ids)],
            'worker_group_ids': [(6, 0, worker_group_ids)],
            'crop_ids': [(6, 0, self.crop_ids.ids)],
            'analytic_group_ids': [(6, 0, self.analytic_group_ids.ids)]
        }

    def action_actualization(self):
        self.ensure_one()
        if self.state not in ('confirm', 'progress'):
            return
        record_id = self.activity_record_ids.filtered(lambda r: r.state == 'draft')
        if not record_id:
            vals = self._prepare_activity_record_vals()
            record_id = self.env['agriculture.daily.activity.record'].with_context(skip_onchange=True).create(vals)
        
        action = {
            'name': _('Plantation Record'),
            'type': 'ir.actions.act_window',
            'res_model': 'agriculture.daily.activity.record',
            'view_mode': 'form',
            'res_id': record_id[0].id,
            'target': 'new'
        }
        self.state = 'progress'
        if self.daily_activity_id and self.daily_activity_id.state == 'confirm':
            self.daily_activity_id.state = 'progress'
        return action

    def action_done(self):
        self.ensure_one()
        moves_to_cancel = (self.material_ids | self.harvest_ids).filtered(lambda m: m.state not in ('cancel', 'done'))
        if moves_to_cancel:
            moves_to_cancel._action_cancel()
        self.state = 'done'

    # approval matrix not implemented yet
    def action_approval(self):
        for record in self:
            record.write({'state': 'to_be_approved'})

    def action_approve(self):
        for record in self:
            record.write({'state': 'approved'})

    def action_reject(self, reason=False):
        for record in self:
            record.write({'state': 'rejected'})

    def button_confirm(self):
        for record in self:
            record.write({'state': 'confirm'})

    def action_view_stock_moves(self, records):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('stock.stock_move_action')
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('stock.view_move_form').id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context') or '{}', self._context), create=False))
        return result

    def action_view_moves(self):
        return self.action_view_stock_moves(self.material_ids + self.harvest_ids)

    def action_view_planting_moves(self):
        self.ensure_one()
        return self.action_view_stock_moves(self.planting_move_ids + self.material_ids)

    def _action_paid(self):
        self.state = 'paid'
