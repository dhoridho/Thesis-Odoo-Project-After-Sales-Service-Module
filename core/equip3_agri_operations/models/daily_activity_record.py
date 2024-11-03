import json
from odoo import models, fields, api, _
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError, ValidationError


class PlantationRecord(models.Model):
    _name = 'agriculture.daily.activity.record'
    _description = 'Plantation Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _register_hook(self):
        super(PlantationRecord, self)._register_hook()
        self._update_daily_activity_type()

    @api.model
    def _update_daily_activity_type(self):
        to_update = self.sudo().search([('daily_activity_type', '=', 'daily_activity')])
        to_update.write({'daily_activity_type': 'plantation'})

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('agriculture.daily.activity.record') or _('New')
        records = super(PlantationRecord, self).create(vals)
        if not self.env.context.get('skip_onchange', False):
            for record in records:
                record._onchange_crop_ids()
        return records

    def write(self, vals):
        res = super(PlantationRecord, self).write(vals)
        records = self.filtered(lambda o: o.state == 'confirm' and o.agreement_id and o.agreement_id.state == 'confirm')
        records.mapped('agreement_id').write({'state': 'progress'})
        return res

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

    def _compute_moves(self):
        for record in self:
            moves = record.material_ids | record.harvest_ids
            if record.activity_harvest_type == 'logging':
                moves |= record.crop_move_ids
            record.moves_count = len(moves.filtered(lambda m: m.state == 'done'))

    def _compute_crops(self):
        crop = self.env['agriculture.crop']
        for record in self:
            record.crops_count = crop.search_count([('origin', '=', record.name)])

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

    @api.depends('activity_line_id')
    def _compute_daily_activity(self):
        for record in self:
            record.daily_activity_id = record.activity_line_id.daily_activity_id

    def _search_estate(self, operator, value):
        return [('block_id.estate_id', operator, value)]

    def _search_division(self, operator, value):
        return [('block_id.division_id', operator, value)]

    @api.depends('transfer_move_ids')
    def _compute_transfer_moves_count(self):
        for record in self:
            record.transfer_moves_count = len(record.transfer_move_ids)

    def _compute_planting_moves_count(self):
        for record in self:
            moves = record.planting_move_ids | record.material_ids
            record.planting_moves_count = len(moves.filtered(lambda m: m.state == 'done'))

    @api.depends('block_id')
    def _compute_allowed_sub_blocks(self):
        for record in self:
            record.allowed_sub_block_ids = [(6, 0, record.block_id.sub_ids.filtered(lambda o: o.state == 'active').ids)]

    @api.model
    def _default_picking_type(self):
        return self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1).id

    daily_activity_type = fields.Selection(
        selection=[('daily_activity', 'Daily Activity'), ('plantation', 'Plantation')], default='plantation', string='Operation Type', required=True)

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', string='Plantation Lines', readonly=True, required=True, ondelete='cascade')
    
    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Plantation Plan', compute=_compute_daily_activity, store=True)
    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, readonly=True)
    category_type = fields.Char(related='activity_id.category_type')
    activity_type = fields.Char(related='activity_id.activity_type')
    activity_harvest_type = fields.Char(related='activity_id.harvest_type')
    
    date_scheduled = fields.Date(string='Scheduled Date', required=True, default=fields.Date.today, readonly=True)
    date_scheduled_end = fields.Date(string='Scheduled Date End', readonly=True)
    block_id = fields.Many2one('crop.block', string='Block', required=True, readonly=True)
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-block', readonly=True, domain="[('id', 'in', allowed_sub_block_ids)]")
    allowed_sub_block_ids = fields.Many2many('crop.block.sub', compute='_compute_allowed_sub_blocks')
    
    analytic_group_ids = fields.Many2many('account.analytic.tag', domain="[('company_id', '=', company_id)]", string="Analytic Group", readonly=True, states={'draft': [('readonly', False)]}, default=_default_analytic_tag_ids)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, required=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, readonly=True, states={'draft': [('readonly', False)]}, required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')
    ], string='Status', default='draft', tracking=True)

    crop_ids = fields.Many2many('agriculture.crop', string='Crops', readonly=True)

    harvest_ids = fields.One2many('stock.move', 'activity_record_harvest_id', string='Harvest')
    material_ids = fields.One2many('stock.move', 'activity_record_material_id', string='Materials')
    asset_ids = fields.One2many('agriculture.daily.activity.asset', 'activity_record_id', string="Assets")

    worker_group_ids = fields.One2many('agriculture.daily.activity.worker', 'activity_record_id', string='Worker Group')

    moves_count = fields.Integer(compute=_compute_moves)
    crops_count = fields.Integer(compute=_compute_crops)

    estate_id = fields.Many2one('crop.estate', related='block_id.estate_id', string='Estate', search=_search_estate)
    division_id = fields.Many2one('agriculture.division', related='block_id.division_id', string='Division', search=_search_division)

    location_id = fields.Many2one('stock.location', string='Location', related='block_id.location_id')
    production_location_id = fields.Many2one('stock.location', string='Production Location', compute=_compute_production_location)
    datetime_scheduled = fields.Datetime(compute=_compute_datetime_scheduled)
    warehouse_id = fields.Many2one('stock.warehouse', compute=_compute_warehouse)

    harvest = fields.Boolean(string='Harvest')
    nursery = fields.Boolean(string='Nursery')
    nursery_ids = fields.One2many('agriculture.daily.activity.nursery', 'activity_record_id', string='Nursery')

    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'activity_record_id', readonly=True)

    crop_age = fields.Selection(
        selection=[
            ('TBM', 'TBM'),
            ('TM', 'TM')
        ],
        string='Crop Age',
        readonly=True
    )

    is_whole_day = fields.Boolean()
    start_time = fields.Datetime()
    end_time = fields.Datetime()

    crop_line_ids = fields.One2many('agriculture.crop.line', 'activity_record_id', string='Crop Lines')
    transfer_move_ids = fields.One2many('stock.move', 'activity_record_transfer_id', string='Transfers')
    transfer_moves_count = fields.Integer(compute=_compute_transfer_moves_count)

    planting_move_ids = fields.One2many('stock.move', 'activity_record_planting_id', string='Planting Moves')
    planting_moves_count = fields.Integer(compute=_compute_planting_moves_count)

    agreement_id = fields.Many2one('agri.agreement', string='Agreement', readonly=True)

    picking_type_id = fields.Many2one('stock.picking.type', default=_default_picking_type)

    planned_size = fields.Float(digits='Product Unit of Measure', string='Planned Area Size', default=1.0, readonly=True)
    size = fields.Float(digits='Product Unit of Measure', string='Area Size', default=1.0, readonly=True, states={'draft': [('readonly', False)]})
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    adjusted_ids = fields.One2many('agri.crop.adjusted', 'activity_record_id', string='Crop Adjuatment')
    adjusted_move_ids = fields.One2many('stock.move', 'activity_record_adj_id', string='Crop Adjustment Moves')

    @api.constrains('daily_activity_type', 'planned_size', 'size')
    def _check_size(self):
        for record in self:
            if record.size <= 0.0:
                raise ValidationError(_('Area size must be positive!'))
            if record.size > record.planned_size:
                raise ValidationError(_('Area size connot be bigger than planned area size!'))

    @api.onchange('block_id')
    def _onchange_block_id(self):
        crop_ids = []
        if self.block_id:
            crop_ids = self.block_id.crop_ids.ids

        self.crop_ids = [(6, 0, crop_ids)]
        if self.nursery_ids:
            self.nursery_ids.update({'block_id': self.block_id.id})

        if self.crop_line_ids:
            self.crop_line_ids.update({'block_id': self.block_id.id})

    @api.onchange('block_id', 'crop_ids', 'activity_type')
    def _onchange_crop_ids(self):
        if self.activity_type not in ('planting', 'crop_adjustment') or self.env.context.get('skip_onchange', False):
            return
        self.nursery_ids = [(5,)] + [(0, 0, {
            'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
            'activity_line_id': self.activity_line_id and self.activity_line_id.id or False,
            'activity_record_id': self.id,
            'block_id': self.block_id.id,
            'product_id': crop.crop.id,
            'uom_id': crop.crop.uom_id.id,
            'count': crop.crop_count,
            'date': fields.Date.today(),
            'lot_id': crop.lot_id.id,
            'current_qty': crop.crop_count
        }) for crop in self.crop_ids]

    @api.onchange('date_scheduled')
    def _onchange_date_scheduled(self):
        if self.nursery_ids:
            self.nursery_ids.update({'date': self.date_scheduled})

    def _update_stock_valuation_layers(self):
        self.ensure_one()
        svl_materials = self.material_ids.stock_valuation_layer_ids
        svl_harvest = self.harvest_ids.stock_valuation_layer_ids

        svl_ids = svl_materials | svl_harvest
        svl_ids.update({
            'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
            'activity_line_id': self.activity_line_id.id,
            'activity_record_id': self.id
        })

        self.write({'stock_valuation_layer_ids': [(6, 0, svl_ids.ids)]})

    @api.constrains('is_whole_day', 'start_time', 'end_time')
    def _check_start_end_time(self):
        for record in self:
            if not record.is_whole_day and record.start_time and record.end_time and record.start_time >= record.end_time:
                raise ValidationError(_('End Time cannot be earlier than Start Time!'))

    def _should_serialize(self):
        self.ensure_one()
        return self.activity_type == 'transfer' and \
            any(line.crop_id.crop.tracking in ('lot', 'serial') for line in self.crop_line_ids) and \
                not self.env.context.get('skip_serializer', False)

    def action_serialize(self):
        self.ensure_one()
        return {
            'name': _('Serializer'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'agri.transfer.serializer',
            'context': {'default_activity_record_id': self.id},
            'target': 'new'
        }

    def action_confirm(self):
        self.ensure_one()
        if self._should_serialize():
            return self.action_serialize()
        
        values = {'state': 'confirm'}
        material_ids = self.material_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if material_ids:

            for move in material_ids:
                if move.quantity_done <= 0.0:
                    raise UserError(_('You need to fill consumed quantity on material firts!'))

                if move.quantity_done > move.availability_uom_qty + move.reserved_availability:
                    raise UserError(_('There is not enough stock for product %s on location %s' % (move.product_id.display_name, move.location_id.display_name)))
            
            material_ids._action_done()

            reference = self.daily_activity_id and self.daily_activity_id.name or self.activity_line_id.name
            material_ids.write({'name': reference, 'origin': reference})
            material_ids.stock_valuation_layer_ids.update({
                'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'activity_line_id': self.activity_line_id.id,
                'activity_record_id': self.id
            })
            values.update({'stock_valuation_layer_ids': [(4, svl.id) for svl in material_ids.stock_valuation_layer_ids]})

        self.write(values)

        if hasattr(self, '_process_%s' % self.activity_type):
            getattr(self, '_process_%s' % self.activity_type)()
            self._account_entry_move()

    def _process_planting(self):
        self.ensure_one()
        for nursery in self.nursery_ids:
            nursery.stock_move_id = self.env['stock.move'].create(nursery._prepare_moves_values())

        moves = self.nursery_ids.mapped('stock_move_id')
        if moves:
            moves._action_done()

    def _process_maintenance(self):
        self.ensure_one()

    def _process_crop_adjustment(self):
        for nursery in self.nursery_ids:
            nursery.crop_id.write({'crop_count': nursery.count})

        move_values = []
        for adjustment in  self.adjusted_ids:
            move_values += [adjustment._prepare_moves_values()]

        if move_values:
            moves = self.env['stock.move'].create(move_values)
            moves._action_done()
            for product in moves.mapped('product_id').filtered(lambda o: o.cost_method == 'average'):
                product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

    def _process_transfer(self):
        self.ensure_one()
        
        Quant = self.env['stock.quant']
        availability = {}
        not_available = []
        
        move_values = []
        for line in self.crop_line_ids:
            product_id = line.crop_id.crop
            location_id = line.block_id.location_id
            quantity = line.uom_id._compute_quantity(line.quantity, product_id.uom_id)

            taken_qty = availability.get(product_id.id, {}).get(location_id, 0.0)
            available_qty = Quant._get_available_quantity(product_id, location_id) - taken_qty

            if quantity > available_qty:
                not_available += [_('- %s on %s' % (product_id.display_name, location_id.display_name))]

            if product_id.id not in availability:
                availability[product_id.id] = {location_id.id: quantity}
            else:
                if location_id.id not in availability[product_id.id]:
                    availability[product_id.id][location_id.id] = quantity
                else:
                    availability[product_id.id][location_id.id] += quantity

            move_values += [line._prepare_moves_values()]

        if not_available:
            raise ValidationError(_("There's not enough quantity of:\n%s" % '\n'.join(list(set(not_available)))))
        
        self.transfer_move_ids = self.env['stock.move'].create(move_values)
        self.transfer_move_ids._action_done()

    def _process_harvest(self):
        self.ensure_one()
        if hasattr(self, '_process_harvest_%s' % self.activity_harvest_type):
            return getattr(self, '_process_harvest_%s' % self.activity_harvest_type)()

    def _process_harvest_fruit_harvesting(self):
        self.ensure_one()
        harvest_ids = self.harvest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if not harvest_ids:
            return
        
        if any(move.quantity_done <= 0 for move in harvest_ids):
            raise UserError(_('You need to fill produced quantity on harvest firts!'))

        harvest_ids._action_done()

        reference = self.daily_activity_id and self.daily_activity_id.name or self.activity_line_id.name
        harvest_ids.write({'name': reference, 'origin': reference})
        harvest_ids.stock_valuation_layer_ids.update({
            'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
            'activity_line_id': self.activity_line_id.id,
            'activity_record_id': self.id
        })
        self.write({'stock_valuation_layer_ids': [(4, svl.id) for svl in harvest_ids.stock_valuation_layer_ids]})

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

    def action_view_transfer_moves(self):
        return self.action_view_stock_moves(self.transfer_move_ids)

    def action_view_planting_moves(self):
        return self.action_view_stock_moves(self.planting_move_ids + self.material_ids)

    def action_view_crops(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('equip3_agri_masterdata.action_agriculture_crop_mgmt')
        records = self.env['agriculture.crop'].search([('origin', '=', self.name)])
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('equip3_agri_masterdata.view_agriculture_crop_mgmt_form').id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context') or '{}', self._context), create=False))
        return result

    def _account_entry_move(self):
        self.ensure_one()
        today = fields.Date.today()
        company_id = self.company_id
        branch_id = self.branch_id

        default_type, default_journal = self.env['ir.property']._get_default_property('property_stock_journal', 'product.category')
        if default_type != 'many2one':
            raise ValidationError(_('Please set default Stock Valuation Journal first!'))

        journal_id = default_journal[1]
        data = getattr(self, '_%s_account_entry_move' % self.activity_type)()

        account_move_values = {
            'journal_id': journal_id,
            'date': today,
            'move_type': 'entry',
            'line_ids': data['lines'],
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'stock_valuation_layer_ids': [(6, 0, data['svl_ids'])]
        }
        account_move_id = self.env['account.move'].create(account_move_values)
        account_move_id._post()
        account_move_id.ref = self.name

    def _planting_account_entry_move(self, with_move=False):
        self.ensure_one()
        svl_ids = (self.material_ids | self.planting_move_ids).mapped('stock_valuation_layer_ids')

        data = {'lines': [], 'svl_ids': svl_ids.ids}
        for svl in svl_ids:
            move_line_values = self._prepare_move_line_vals(svl.product_id, svl.quantity)
            if svl.stock_move_id.activity_record_material_id:
                move_line_values['credit'] = abs(svl.value)
            else:
                move_line_values['debit'] = abs(svl.value)

            if with_move:
                move_line_values['stock_move_id'] = svl.stock_move_id.id

            data['lines'] += [(0, 0, move_line_values)]
        return data
    
    def _maintenance_account_entry_move(self, with_move=False):
        self.ensure_one()
        material_svl_ids = self.material_ids.mapped('stock_valuation_layer_ids')
        material_value = sum(material_svl_ids.mapped('value'))
        currency_id = self.company_id.currency_id

        data = {'lines': [], 'svl_ids': material_svl_ids.ids}

        for svl in material_svl_ids:
            move_line_values = self._prepare_move_line_vals(svl.product_id, svl.quantity)
            move_line_values['credit'] = currency_id.round(abs(svl.value))
            if with_move:
                move_line_values['stock_move_id'] = svl.stock_move_id.id
            data['lines'] += [(0, 0, move_line_values)]

        crops_total_quantity = sum([crop.uom_id._compute_quantity(crop.crop_count, crop.crop.uom_id) for crop in self.crop_ids])

        for crop in self.crop_ids:
            product_id = crop.crop
            quantity = crop.uom_id._compute_quantity(crop.crop_count, product_id.uom_id)
            value = (quantity / crops_total_quantity) * material_value

            move_line_values = self._prepare_move_line_vals(product_id, quantity)
            move_line_values['debit'] = currency_id.round(abs(value))
            if with_move:
                move_line_values['stock_move_line_id'] = crop.move_line_id.id
            data['lines'] += [(0, 0, move_line_values)]

        total_debit = sum([line[-1]['debit'] for line in data['lines']])
        total_credit = sum([line[-1]['credit'] for line in data['lines']])
        difference = total_debit - total_credit
        
        if not currency_id.is_zero(difference):
            default_type, default_account = self.env['ir.property']._get_default_property('property_stock_valuation_account_id', 'product.category')
            if default_type != 'many2one':
                raise ValidationError(_('Please set default Stock Valuation Account first!'))
            account_id = default_account[1]

            correction_values = self._prepare_move_line_vals(self.env['product.product'], 0)
            correction_values.update({
                'name': _('Rounding correction'),
                'account_id': account_id,
                'debit': -difference if difference < 0.0  else 0.0,
                'credit': difference if difference > 0.0 else 0.0
            })
            data['lines'] += [(0, 0, correction_values)]

        return data

    def _crop_adjustment_account_entry_move(self, with_move=False):
        return self._planting_account_entry_move(with_move=with_move)

    def _transfer_account_entry_move(self, with_move=False):
        self.ensure_one()
        material_svl_ids = self.material_ids.stock_valuation_layer_ids
        material_value = sum(material_svl_ids.mapped('value'))

        data = {'lines': [], 'svl_ids': material_svl_ids.ids}

        for svl in material_svl_ids:
            move_line_values = self._prepare_move_line_vals(svl.product_id, svl.quantity)
            move_line_values['credit'] = abs(svl.value)
            if with_move:
                move_line_values['stock_move_id'] = svl.stock_move_id.id
            data['lines'] += [(0, 0, move_line_values)]

        transfer_total_quantity = sum([t.product_uom._compute_quantity(t.product_uom_qty, t.crop_id.crop.uom_id) for t in self.transfer_move_ids])

        for transfer_line in self.transfer_move_ids:
            product_id = transfer_line.crop_id.crop
            quantity = transfer_line.uom_id._compute_quantity(transfer_line.quantity, product_id.uom_id)
            value = (quantity / transfer_total_quantity) * material_value

            move_line_values = self._prepare_move_line_vals(product_id, quantity)
            move_line_values['debit'] = abs(value)
            if with_move:
                move_line_values['stock_move_id'] = transfer_line.id
            data['lines'] += [(0, 0, move_line_values)]
        return data

    def _harvest_account_entry_move(self, with_move=False):
        self.ensure_one()
        svl_ids = (self.material_ids | self.harvest_ids).mapped('stock_valuation_layer_ids')

        data = {'lines': [], 'svl_ids': svl_ids.ids}
        for svl in svl_ids:
            move_line_values = self._prepare_move_line_vals(svl.product_id, svl.quantity)
            if svl.stock_move_id.activity_record_material_id:
                move_line_values['credit'] = abs(svl.value)
            else:
                move_line_values['debit'] = abs(svl.value)

            if with_move:
                move_line_values['stock_move_id'] = svl.stock_move_id.id

            data['lines'] += [(0, 0, move_line_values)]
        return data
    
    def _prepare_move_line_vals(self, product_id, quantity):
        account_id = product_id.categ_id.property_stock_valuation_account_id
        return {
            'name': product_id.display_name,
            'ref': product_id.display_name,
            'product_id': product_id.id,
            'product_uom_id': product_id.uom_id.id,
            'quantity': quantity,
            'account_id': account_id.id,
            'debit': 0.0,
            'credit': 0.0
        }


class AgricultureCropLine(models.Model):
    _name = 'agriculture.crop.line'
    _description = 'Agriculture Crop Line'

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record', required=True, ondelete='cascade')
    crop_id = fields.Many2one('agriculture.crop', string='Crop', required=True)
    block_id = fields.Many2one('crop.block', string='Current Block', required=True)
    block_crop_ids = fields.One2many(related='block_id.crop_ids')
    dest_block_id = fields.Many2one('crop.block', string='Destination Block', required=True)
    quantity = fields.Float(default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    lot_data = fields.Text()

    @api.onchange('crop_id')
    def _onchange_crop_id(self):
        self.uom_id = self.crop_id and self.crop_id.crop.uom_id.id or False

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0.0:
                raise ValidationError(_('Quantity must be positive!'))

    def _prepare_moves_values(self):
        self.ensure_one()
        location_id = self.block_id.location_id
        location_dest_id = self.dest_block_id.location_id
        company_id = self.activity_record_id.company_id
        branch_id = self.activity_record_id.branch_id

        values = {
            'name': self.activity_record_id.name,
            'origin': self.activity_record_id.name,
            'product_id': self.crop_id.crop.id,
            'product_uom': self.uom_id.id,
            'date': fields.Date.today(),
            'product_uom_qty': self.quantity,
            'quantity_done': self.quantity,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'crop_line_id': self.id,
            'company_id': company_id.id,
            'branch_id': branch_id.id
        }
        if self.lot_data:
            lot_data = json.loads(self.lot_data)['data']

            move_line_values = []
            for line in lot_data:
                move_line_values += [(0, 0, {
                    'product_id': line['product_id'],
                    'product_uom_id': line['uom_id'],
                    'qty_done': line['product_uom_qty'],
                    'lot_id': line['lot_id'],
                    'location_id': location_id.id,
                    'location_dest_id': location_dest_id.id,
                    'company_id': company_id.id,
                })]

            values.update({'move_line_ids': move_line_values})
        return values


class AgriCropAdjusted(models.Model):
    _name = 'agri.crop.adjusted'
    _description = 'Agriculture Crop Adjustment'

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', required=True, ondelete='cascade')
    crop_id = fields.Many2one('agriculture.crop', string='Crop', required=True)
    current_qty = fields.Float(string='Current Quantity', digits='Product Unit of Measure')
    counted_qty = fields.Float(string='Counted Qauntity', digits='Product Unit of Measure')

    @api.onchange('crop_id')
    def _onchange_crop_id(self):
        if self.crop_id:
            self.current_qty = self.crop_id.crop_count

    def _prepare_moves_values(self):
        self.ensure_one()
        activity_record_id = self.activity_record_id
        activity_line_id = activity_record_id.activity_line_id
        activity_plan_id = activity_line_id.daily_activity_id

        product_id = self.crop_id.crop
        uom_id = self.crop_id.uom_id

        company_id = activity_record_id.company_id
        branch_id = activity_record_id.branch_id
        block_location = activity_record_id.block_id.location_id
        virtual_location = product_id.with_company(company_id).property_stock_inventory
        reference = activity_record_id.name

        difference_qty = self.counted_qty - self.current_qty
        if difference_qty > 0.0:
            location_id = virtual_location
            location_dest_id = block_location
        else:
            location_id = block_location
            location_dest_id = virtual_location

        values = {
            'name': reference,
            'origin': reference,
            'product_id': product_id.id,
            'product_uom': uom_id.id,
            'date': fields.Date.today(),
            'product_uom_qty': abs(difference_qty),
            'quantity_done': abs(difference_qty),
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'activity_record_adj_id': activity_record_id.id,
            'activity_line_adj_id': activity_line_id.id,
            'activity_plan_adj_id': activity_plan_id.id,
            'company_id': company_id.id,
            'branch_id': branch_id.id,
            'adjustment_id': self.id,
            'price_unit': 0.0
        }

        if product_id.tracking in ('lot', 'serial'):
            move_line_values = [(0, 0, {
                'product_id': product_id.id,
                'product_uom_id': uom_id.id,
                'qty_done': abs(difference_qty),
                'lot_id': self.crop_id.lot_id.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': company_id.id
            })]
            values.update({'move_line_ids': move_line_values})
        return values
