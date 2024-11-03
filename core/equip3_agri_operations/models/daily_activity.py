from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime


class PlantationPlan(models.Model):
    _name = 'agriculture.daily.activity'
    _description = 'Plantation Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _register_hook(self):
        super(PlantationPlan, self)._register_hook()
        self._update_daily_activity_type()

    @api.model
    def _update_daily_activity_type(self):
        to_update = self.sudo().search([('daily_activity_type', '=', 'daily_activity')])
        to_update.write({'daily_activity_type': 'plantation'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.daily.activity') or _('New')
        records = super(PlantationPlan, self).create(vals)
        records._assign_activity_lines()
        return records

    def write(self, vals):
        res = super(PlantationPlan, self).write(vals)
        self._assign_activity_lines()
        return res

    def _assign_activity_lines(self):
        for record in self:
            if record.state != 'draft':
                continue
            for line in record.line_ids:
                material_ids = record.material_ids.filtered(lambda m: m.activity_line_sequence == line.sequence)
                harvest_ids = record.harvest_ids.filtered(lambda m: m.activity_line_sequence == line.sequence)
                nursery_ids = record.nursery_ids.filtered(lambda m: m.activity_line_sequence == line.sequence)
                asset_ids = record.asset_ids.filtered(lambda m: m.activity_line_sequence == line.sequence)
                line.write({
                    'material_ids': [(6, 0, material_ids.ids)],
                    'harvest_ids': [(6, 0, harvest_ids.ids)],
                    'nursery_ids': [(6, 0, nursery_ids.ids)],
                    'asset_ids': [(6, 0, asset_ids.ids)]
                })

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
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.agriculture_daily_activity:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['agri.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'ada')
        ], limit=1).id

    @api.model
    def _default_analytic_tag_ids(self, force_company=False, force_branch=False):
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

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = []
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'ada_id': record.id,
                        'line_id': line.id,
                        'sequence': line.sequence,
                        'minimum_approver': line.minimum_approver,
                        'approver_ids': [(6, 0, line.approver_ids.ids)]
                    })]
            record.approval_matrix_line_ids = lines

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.need_action_ids', 'is_matrix_on')
    def _compute_user_is_approver(self):
        user = self.env.user
        for record in self:
            need_action_ids = record.approval_matrix_line_ids.mapped('need_action_ids')
            record.user_is_approver = user in need_action_ids and record.is_matrix_on

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

    @api.depends('line_ids')
    def _compute_next_sequence(self):
        for record in self:
            record.next_sequence = len(record.line_ids)

    @api.depends('line_ids', 'line_ids.harvest')
    def _compute_harvest(self):
        for record in self:
            record.harvest = any(record.line_ids.mapped('harvest'))

    @api.depends('line_ids', 'line_ids.nursery')
    def _compute_nursery(self):
        for record in self:
            record.nursery = any(record.line_ids.mapped('nursery'))

    @api.depends('line_ids', 'line_ids.activity_id')
    def _compute_activity_ids(self):
        for record in self:
            record.crop_activity_ids = [(6, 0, record.line_ids.mapped('activity_id').ids)]

    @api.depends('crop_activity_ids')
    def _compute_activity_types(self):
        for record in self:
            record.any_maintenance = any(act.activity_type == 'maintenance' for act in record.crop_activity_ids)
            record.any_planting = any(act.activity_type == 'planting' for act in record.crop_activity_ids)
            record.any_crop_adjustment = any(act.activity_type == 'crop_adjustment' for act in record.crop_activity_ids)
            record.any_transfer = any(act.activity_type == 'transfer' for act in record.crop_activity_ids)
            record.any_harvest = any(act.activity_type == 'harvest' for act in record.crop_activity_ids)

    def _compute_planting_moves_count(self):
        for record in self:
            moves = record.planting_move_ids | record.material_ids
            record.planting_moves_count = len(moves.filtered(lambda m: m.state == 'done'))

    def _compute_moves(self):
        for record in self:
            moves = record.material_ids | record.harvest_ids
            if record.any_harvest_logging:
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
        selection=[('daily_activity', 'Daily Activity'), ('plantation', 'Plantation')], default='plantation', string='Operation Type', required=True, ondelete={'daily_activiy': 'plantation'})

    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    name = fields.Char(string='Plantation Plan', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    
    date_scheduled = fields.Date(string='Scheduled Date', required=True, default=fields.Date.today, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    date_scheduled_end = fields.Date(string='Scheduled Date End', compute=_compute_date_scheduled_end)
    
    block_id = fields.Many2one('crop.block', string='Block', required=True, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-block', readonly=True, states={'draft': [('readonly', False)]}, domain="[('id', 'in', allowed_sub_block_ids)]", tracking=True)
    allowed_sub_block_ids = fields.Many2many('crop.block.sub', compute='_compute_allowed_sub_blocks')

    crop_ids = fields.Many2many('agriculture.crop', string='Crop', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible', required=True, default=lambda self: self.env.user, readonly=True, states={'draft': [('readonly', False)]}, tracking=True)

    analytic_group_ids = fields.Many2many('account.analytic.tag', domain="[('company_id', '=', company_id)]", string="Analytic Group", readonly=True, states={'draft': [('readonly', False)]}, default=_default_analytic_tag_ids)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, required=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, readonly=True, states={'draft': [('readonly', False)]}, required=True, tracking=True)
    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)

    approval_matrix_id = fields.Many2one(
        comodel_name='agri.approval.matrix', 
        domain="""[
            ('matrix_type', '=', 'ada'),
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix',
        default=_default_approval_matrix)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='agri.approval.matrix.entry',
        inverse_name='ada_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(related='company_id.agriculture_daily_activity')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('agriculture.daily.activity.line', 'daily_activity_id', string='Plantation Lines')
    crop_activity_ids = fields.Many2many('crop.activity', compute=_compute_activity_ids)

    any_maintenance = fields.Boolean(compute=_compute_activity_types)
    any_planting = fields.Boolean(compute=_compute_activity_types)
    any_crop_adjustment = fields.Boolean(compute=_compute_activity_types)
    any_transfer = fields.Boolean(compute=_compute_activity_types)
    any_harvest = fields.Boolean(compute=_compute_activity_types)

    material_ids = fields.One2many('stock.move', 'daily_activity_material_id', string='Materials', readonly=False)
    harvest_ids = fields.One2many('stock.move', 'daily_activity_harvest_id', string='Harvest', readonly=False)
    nursery_ids = fields.One2many('agriculture.daily.activity.nursery', 'daily_activity_id', string='Nursery')
    asset_ids = fields.One2many('agriculture.daily.activity.asset', 'daily_activity_id', string='Assets', readonly=False)
    
    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')
    state_2 = fields.Selection(related='state', tracking=False, string='State 2')
    state_3 = fields.Selection(related='state', tracking=False, string='State 3')

    next_sequence = fields.Integer(compute=_compute_next_sequence)

    estate_id = fields.Many2one('crop.estate', related='block_id.estate_id')
    location_id = fields.Many2one('stock.location', string='Location', related='block_id.location_id')
    production_location_id = fields.Many2one('stock.location', string='Production Location', compute=_compute_production_location)
    datetime_scheduled = fields.Datetime(compute=_compute_datetime_scheduled)
    warehouse_id = fields.Many2one('stock.warehouse', compute=_compute_warehouse)
    
    harvest = fields.Boolean(compute=_compute_harvest, store=True, string='Harvest')
    nursery = fields.Boolean(compute=_compute_nursery, store=True, string='Nursery')

    worker_group_ids = fields.One2many('agriculture.daily.activity.worker', 'daily_activity_id', string='Worker Group')
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'daily_activity_id', readonly=True)
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

    picking_type_id = fields.Many2one('stock.picking.type', default=_default_picking_type)

    size = fields.Float(digits='Product Unit of Measure', string='Area Size', default=1.0, readonly=True, states={'draft': [('readonly', False)]})
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    def _check_notification(self, res_id):
        daily_activity = self.browse(res_id)
        if not daily_activity:
            return
        if daily_activity.state != 'draft':
            return
        approval_matrix = daily_activity.approval_matrix_id
        if not approval_matrix:
            approval_matrix = self.env['agri.approval.matrix'].search([
                ('company_id', '=', daily_activity.company_id.id),
                ('branch_id', '=', daily_activity.branch_id.id),
                ('matrix_type', '=', 'ada')
            ], limit=1)
            if not approval_matrix:
                return

        options = {'post_log': True, 'send_system': True, 'send_email': True}
        now_formatted = format_datetime(self.env, fields.Datetime.now())
        approval_matrix.process_notifications(daily_activity, options, now_formatted)

    def _get_material_values(self):
        self.ensure_one()
        material_vals = []
        seq = 0
        for line in self.line_ids:
            if not line.activity_id:
                continue
            for material in line.activity_id.material_ids:
                product_id = material.product_id
                material_vals += [{
                    'daily_activity_material_id': self.id,
                    'activity_line_sequence': line.sequence,
                    'activity_line_material_id': line.id,
                    'activity_material_id': material.id,
                    'sequence': seq,
                    'name': self.name,
                    'date': self.datetime_scheduled,
                    'date_deadline': self.datetime_scheduled,
                    'product_id': product_id.id,
                    'product_uom_qty': material.quantity,
                    'product_uom': material.uom_id.id,
                    'quantity_done': material.quantity,
                    'location_id': self.location_id.id,
                    'location_dest_id': product_id.with_company(self.company_id).property_stock_production.id,
                    'company_id': self.company_id.id,
                    'price_unit': product_id.standard_price,
                    'origin': self.name,
                    'state': 'draft',
                    'warehouse_id': self.location_id.get_warehouse().id,
                    'picking_type_id': self.picking_type_id.id
                }]
                seq += 1
        return material_vals

    def _get_harvest_values(self):
        self.ensure_one()
        harvest_vals = []
        seq = 0
        for line in self.line_ids:
            if not line.activity_id:
                continue
            if not line.activity_id.group_id:
                continue
            if not line.activity_id.group_id.category_id:
                continue
            if line.activity_id.group_id.category_id.value != 'harvest':
                continue
            for harvest in line.activity_id.harvest_ids:
                harvest_vals += [{
                    'daily_activity_harvest_id': self.id,
                    'activity_line_sequence': line.sequence,
                    'activity_line_harvest_id': line.id,
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
                seq += 1
        return harvest_vals

    def _get_nursery_values(self):
        self.ensure_one()
        nursery_vals = []
        seq = 0
        for line in self.line_ids:
            if not line.activity_id:
                continue
            if not line.activity_id.group_id:
                continue
            if not line.activity_id.group_id.category_id:
                continue
            if line.activity_id.group_id.category_id.value != 'nursery':
                continue
            for nursery in line.activity_id.crop_ids:
                nursery_vals += [{
                    'daily_activity_id': self.id,
                    'activity_line_sequence': line.sequence,
                    'activity_line_id': line.id,
                    'product_id': nursery.product_id.id,
                    'block_id': self.block_id.id,
                    'count': nursery.product_uom_qty,
                    'date': self.date_scheduled,
                    'uom_id': nursery.product_uom_id.id
                }]
                seq += 1
        return nursery_vals

    def _get_asset_values(self):
        self.ensure_one()
        asset_vals = []
        seq = 0
        for line in self.line_ids:
            if not line.activity_id:
                continue
            for asset in line.activity_id.asset_ids:
                asset_vals += [{
                    'daily_activity_id': self.id,
                    'activity_line_sequence': line.sequence,
                    'activity_line_id': line.id,
                    'activity_asset_id': asset.id,
                    'asset_id': asset.asset_id.id,
                    'user_id': asset.user_id.id,
                    'original_move': True
                }]
                seq += 1
        return asset_vals

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        self.material_ids = [(5,)] + [(0, 0, vals) for vals in self._get_material_values()]
        self.harvest_ids = [(5,)] + [(0, 0, vals) for vals in self._get_harvest_values()]
        self.nursery_ids = [(5,)] + [(0, 0, vals) for vals in self._get_nursery_values()]
        self.asset_ids = [(5,)] + [(0, 0, vals) for vals in self._get_asset_values()]

    @api.onchange('priority', 'branch_id', 'analytic_group_ids', 'date_scheduled', 'block_id', 'is_whole_day', 'start_time', 'end_time')
    def _set_line_ids(self):
        self.line_ids.update({
            'priority': self.priority,
            'branch_id': self.branch_id.id,
            'analytic_group_ids': [(6, 0, self.analytic_group_ids.ids)],
            'date_scheduled': self.date_scheduled,
            'block_id': self.block_id.id,
            'is_whole_day': self.is_whole_day,
            'start_time': self.start_time,
            'end_time': self.end_time
        })

    @api.constrains('daily_activity_type', 'size')
    def _check_size(self):
        for record in self:
            if record.size <= 0.0:
                raise ValidationError(_('Area size must be positive!'))

    @api.onchange('size')
    def _onchange_size(self):
        self.line_ids.update({'size': self.size})

    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        self.line_ids.update({'uom_id': self.uom_id.id})

    @api.onchange('block_id')
    def _onchange_block_id(self):
        crop_ids = []
        if self.block_id:
            crop_ids = self.block_id.crop_ids.ids
            
        self.crop_ids = [(6, 0, crop_ids)]
        if self.nursery_ids:
            self.nursery_ids.update({'block_id': self.block_id.id})

        if not self.sub_block_id:
            self.size = self.block_id.size
            self.uom_id = self.block_id.uom_id.id

    @api.onchange('sub_block_id')
    def _onchange_sub_block_id(self):
        if self.sub_block_id:
            self.size = self.sub_block_id.size
            self.uom_id = self.sub_block_id.uom_id.id
        self.line_ids.update({'sub_block_id': self.sub_block_id.id})

    @api.onchange('date_scheduled')
    def _onchange_date_scheduled(self):
        if self.nursery_ids:
            self.nursery_ids.update({'date': self.date_scheduled})

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.agriculture_daily_activity_wa_notif
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'to_be_approved'})
            record.line_ids.action_approval()

    @api.constrains('is_whole_day', 'start_time', 'end_time')
    def _check_start_end_time(self):
        for record in self:
            if not record.is_whole_day and record.start_time and record.end_time and record.start_time >= record.end_time:
                raise ValidationError(_('End Time cannot be earlier than Start Time!'))

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})
                record.line_ids.action_approve()

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})
                record.line_ids.action_reject()

    def button_confirm(self):
        for record in self:
            matrix_is_on = record.is_matrix_on
            state = record.state
            if (matrix_is_on and state != 'approved') or (not matrix_is_on and state != 'draft'):
                continue
            record.state = 'confirm'
            record.line_ids.button_confirm()

    def button_done(self):
        self.ensure_one()
        if self.line_ids and not all(line.state == 'done' for line in self.line_ids):
            raise UserError(_('There are some %s Lines needs to be done first!' % self.daily_activity_type.title()))
        self.state = 'done'

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
