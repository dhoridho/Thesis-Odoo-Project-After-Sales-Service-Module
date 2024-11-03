from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MiningDailyPorductionReord(models.Model):
    _name = 'mining.daily.production.record'
    _description = 'Mining Daily Production Record'
    _order = 'id desc'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            opr_type_id = vals.get("selected_operation_type")
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'mining.daily.production.record.seqs.%s' % opr_type_id, sequence_date=None) or _('New')
        return super(MiningDailyPorductionReord, self).create(vals)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.selected_operation_type in ['extraction', 'waste_removal', 'hauling', 'processing']:
                continue
            if record.end_date < record.start_date:
                raise ValidationError("End Date cannot be Earlier than Start Date")

    @api.depends('production_record_ids.gross_total', 'production_record_ids.nett_total',
                 'production_record_ids.input_total', 'production_record_ids.output_total',
                 'production_record_ids.loss_total')
    def _compute_totals(self):
        for record in self:
            record.gross_total = sum(record.production_record_ids.mapped('gross_total'))
            record.nett_total = sum(record.production_record_ids.mapped('nett_total'))
            record.input_total = sum(record.production_record_ids.mapped('input_total'))
            record.output_total = sum(record.production_record_ids.mapped('output_total'))
            record.loss_total = sum(record.production_record_ids.mapped('loss_total'))

    @api.depends('production_record_ids', 'production_record_ids.stock_move_ids')
    def _compute_stock_move(self):
        for record in self:
            moves = record.production_record_ids.stock_move_ids
            record.stock_moves_count = len(moves)

    name = fields.Char(required=True, copy=False, readonly=True, default=_('New'), tracking=True, string='Reference')
    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site', readonly=True, states={'draft': [('readonly', False)]}, domain="['&', '|', ('company_id', '=', False), ('company_id', '=', company_id), '|', ('branch_id', '=', False), ('branch_id', '=', branch_id)]")

    mining_operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, readonly=True, states={'draft': [('readonly', False)]}, domain="[('site_id', '=', mining_site_id), ('operation_type_id', '=', selected_operation_type)]")

    vessel_id = fields.Many2one(comodel_name='maintenance.equipment', string='Vessel', domain="[('vehicle_checkbox', '=', True)]", readonly=True, states={'draft': [('readonly', False)]})
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sales Order', domain="[('state', '=', 'sale')]", readonly=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', related='sale_order_id.partner_id', readonly=True, states={'draft': [('readonly', False)]})
    source_location_id = fields.Many2one(comodel_name='stock.location', string='Source Location', readonly=True, states={'draft': [('readonly', False)]})
    destination_location_id = fields.Many2one(comodel_name='stock.location', string='Destination Location', readonly=True, states={'draft': [('readonly', False)]})
    incoterm = fields.Selection([
        ('fob', 'FOB'),
        ('cif', 'CIF'),
    ], string='Incoterm', readonly=True, states={'draft': [('readonly', False)]})
    schedule_date = fields.Datetime(string="Schedule Date", readonly=True, states={'draft': [('readonly', False)]})

    start_date = fields.Datetime(string="Start Date", readonly=True, states={'draft': [('readonly', False)]})
    end_date = fields.Datetime(string="End Date", readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date(string="Date", readonly=True, states={'draft': [('readonly', False)]})
    gross_total = fields.Float(string='Gross Total', readonly=True, compute='_compute_totals', store=True)
    gross_uom_id = fields.Many2one(comodel_name='uom.uom', string='Gross UOM', readonly=True)
    nett_total = fields.Float(string='Nett Total', readonly=True, compute='_compute_totals', store=True)
    nett_uom_id = fields.Many2one(comodel_name='uom.uom', string='Nett UOM', readonly=True)

    input_total = fields.Float(string='Input Total', readonly=True, compute='_compute_totals', store=True)
    input_uom_id = fields.Many2one(comodel_name='uom.uom', string='Input UOM', readonly=True)
    output_total = fields.Float(string='Output Total', readonly=True, compute='_compute_totals', store=True)
    output_uom_id = fields.Many2one(comodel_name='uom.uom', string='Output UOM', readonly=True)
    loss_total = fields.Float(string='Loss Total', readonly=True, compute='_compute_totals', store=True)
    loss_uom_id = fields.Many2one(comodel_name='uom.uom', string='Loss UOM', readonly=True)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, readonly=True, states={'draft': [('readonly', False)]})
    create_uid = fields.Many2one(comodel_name='res.users', string='Created By', default=lambda self: self.env.user)

    production_record_ids = fields.One2many('mining.production.record', 'daily_production_id', string='Production', readonly=True, states={'draft': [('readonly', False)]})
    selected_operation_type = fields.Char(string="Selected Operation Type")

    production_target = fields.Float(string='Daily Target', digits='Product Unit of Measure', readonly=True)

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm')
    ], default='draft', string='Status', readonly=True)

    stock_move_ids = fields.One2many('stock.move', 'mining_production_order_id', string='Stock Moves', readonly=True)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mining_production_order_id', string='Valuations', readonly=True)
    stock_moves_count = fields.Integer(compute=_compute_stock_move)

    def action_create_record(self):
        self.ensure_one()
        title = self.selected_operation_type.replace('_', '').title()
        return {
            'name': _('%s Record' % title),
            'type': 'ir.actions.act_window',
            'res_model': 'mining.production.record',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_daily_production_id': self.id,
                'default_selected_operation_type': self.selected_operation_type,
            }
        }

    @api.onchange('mining_site_id', 'mining_operation_id', 'date')
    def _onchange_production_target(self):
        if self.selected_operation_type not in ['extraction', 'waste_removal', 'hauling', 'processing'] or not self.date:
            return
        month_line_id = self.env['mining.planning.production'].search([
            ('mining_planning_id.mining_site_id', '=', self.mining_site_id.id),
            ('mining_planning_id.mining_operation_id', '=', self.mining_operation_id.id),
            ('production_date', '=', self.date)
        ], limit=1)
        self.production_target = month_line_id.adjusted_target
       
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            vals_line = []
            do_obj = self.env['stock.picking'].search([('sale_id', '=', self.sale_order_id.id)])
            do_lines = do_obj.move_lines.filtered(lambda r: r.product_id.type == 'product')
            for line in do_lines:
                vals_line.append((0, 0, {
                    'product_id': line.product_id.id,
                    'remaining': line.remaining,
                    'product_uom_qty': line.product_uom_qty,
                    'quantity_done': line.quantity_done,
                    'product_uom': line.product_uom.id,
                }))
            self.production_record_ids = None
            self.production_record_ids = vals_line
            self.destination_location_id = do_obj.location_dest_id

    @api.onchange('company_id', 'branch_id')
    def _onchange_company_id(self):
        company_id = self.company_id.id
        branch_id = self.branch_id.id
        self.mining_site_id = self.env['mining.site.control'].search([
            ('company_id', '=', company_id), ('branch_id', '=', branch_id)
        ], limit=1).id

    @api.onchange('mining_site_id', 'selected_operation_type')
    def _onchange_mining_site_id(self):
        if not self.mining_site_id:
            return
        operation_ids = self.mining_site_id.operation_ids.filtered(lambda r: r.operation_type_id == self.selected_operation_type).ids
        if operation_ids:
            self.mining_operation_id = operation_ids[0]

    @api.onchange('mining_operation_id')
    def _onchange_operation_id(self):
        if self.mining_operation_id:
            self.gross_uom_id = self.mining_operation_id.uom_id.id
            self.nett_uom_id = self.mining_operation_id.uom_id.id
            self.input_uom_id = self.mining_operation_id.uom_id.id
            self.output_uom_id = self.mining_operation_id.uom_id.id
            self.loss_uom_id = self.mining_operation_id.uom_id.id

            if self.selected_operation_type == 'shipment':
                self.source_location_id = self.mining_operation_id.location_src_id.id
                self.destination_location_id = self.mining_operation_id.location_dest_id.id

    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirm'

    def action_view_stock_moves(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('stock.stock_move_action')
        records = self.stock_move_ids
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


class MiningPorductionReord(models.Model):
    _name = 'mining.production.record'
    _description = 'Mining Production Record'
    _order = 'id desc'

    @api.model
    def create(self, vals):
        res = super(MiningPorductionReord, self).create(vals)
        if res.name == _('New'):
            opr_type_id = res.selected_operation_type
            res.name = self.env['ir.sequence'].next_by_code(
                'mining.production.record.seqs.%s' % opr_type_id, sequence_date=None) or _('New')
            if opr_type_id == 'shipment':
                res.mining_site_id = None
                res.mining_operation_id = None
                res.gross_uom_id = None
                res.tare_uom_id = None
                res.nett_uom_id = None
                res.input_uom_id = None
                res.output_uom_id = None
                res.loss_uom_id = None
                res.branch_id = None
        return res

    @api.depends('stock_move_ids')
    def _compute_stock_move(self):
        for record in self:
            record.stock_moves_count = len(record.stock_move_ids)

    @api.depends('mining_operation_id')
    def _compute_allowed_products(self):
        for record in self:
            record.allowed_product_ids = [(6, 0, record.mining_operation_id.line_ids.mapped('product_id').ids)]

    daily_production_id = fields.Many2one('mining.daily.production.record', ondelete='cascade')

    name = fields.Char(required=True, copy=False, readonly=True, default=_('New'), tracking=True, string='Reference')

    mining_site_id = fields.Many2one(comodel_name='mining.site.control', string='Mining Site', readonly=True)
    mining_pit_id = fields.Many2one(comodel_name='mining.project.control', string='Mining Pit')
    mining_operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', readonly=True)
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment', domain="[('vehicle_checkbox', '=', True)]")
    transport_id = fields.Many2one(comodel_name='maintenance.equipment', string='Transport', domain="[('vehicle_checkbox', '=', True)]")
    processing_location_id = fields.Many2one(comodel_name='stock.location', string='Processing Location')
    source_location_id = fields.Many2one(comodel_name='stock.location', string='Location')
    destination_location_id = fields.Many2one(comodel_name='stock.location', string='Destination Location')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', ondelete='set null', domain="[('id', 'in', allowed_product_ids)]")
    allowed_product_ids = fields.Many2many(comodel_name='product.product', compute=_compute_allowed_products)
    
    gross_total = fields.Float(string='Gross')
    gross_uom_id = fields.Many2one(comodel_name='uom.uom', string='Gross UOM', readonly=True)
    tare_total = fields.Float(string='Tare')
    tare_uom_id = fields.Many2one(comodel_name='uom.uom', string='Tare UOM', readonly=True)
    nett_total = fields.Float(string='Nett', readonly=True)
    nett_uom_id = fields.Many2one(comodel_name='uom.uom', string='Nett UOM', readonly=True)

    input_total = fields.Float(string='Input Total', readonly=True, compute='_compute_input_totals', store=True)
    input_uom_id = fields.Many2one(comodel_name='uom.uom', string='Input UOM', readonly=True)
    output_total = fields.Float(string='Output Total', readonly=True, compute='_compute_output_totals', store=True)
    output_uom_id = fields.Many2one(comodel_name='uom.uom', string='Output UOM', readonly=True)
    loss_total = fields.Float(string='Loss Total', readonly=True)
    loss_uom_id = fields.Many2one(comodel_name='uom.uom', string='Loss UOM', readonly=True)

    prod_rec_date = fields.Date(string="Date")

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    create_uid = fields.Many2one(comodel_name='res.users', string='Created By', default=lambda self: self.env.user)

    selected_operation_type = fields.Char(string="Selected Operation Type", related='daily_production_id.selected_operation_type')
    production_record_input_ids = fields.One2many('mining.production.record.line.input', 'production_record_input_id', string='Production Record Input')
    production_record_output_ids = fields.One2many('mining.production.record.line.output', 'production_record_output_id', string='Production Record Output')

    description = fields.Char(related='product_id.product_tmpl_id.name', string="Description")
    remaining = fields.Float(string="Remaining")
    product_uom_qty = fields.Float(string="Demand")
    quantity_done = fields.Float(string="Done")
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')

    stock_move_ids = fields.One2many('stock.move', 'mining_production_record_id', string='Stock Moves', readonly=True)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mining_production_record_id', string='Valuations', readonly=True)
    stock_moves_count = fields.Integer(compute=_compute_stock_move)
    
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', string='Status', readonly=True)

    def _create_extraction_move(self):
        self.ensure_one()
        StockMove = self.env['stock.move']
        production_location = self.product_id.with_company(self.company_id).property_stock_production
        move_values = [self._prepare_stock_move_values(production_location, self.source_location_id)]
        if self.destination_location_id:
            move_values += [self._prepare_stock_move_values(self.source_location_id, self.destination_location_id)]
        return StockMove.create(move_values)

    def _create_waste_removal_move(self):
        self.ensure_one()
        StockMove = self.env['stock.move']
        production_location = self.product_id.with_company(self.company_id).property_stock_production
        move_values = [self._prepare_stock_move_values(production_location, self.source_location_id)]
        if self.destination_location_id:
            move_values += [self._prepare_stock_move_values(self.source_location_id, self.destination_location_id)]
        return StockMove.create(move_values)

    def _create_hauling_move(self):
        self.ensure_one()

        not_available = []
        availability = {}
        Quant = self.env['stock.quant']

        product_id = self.product_id
        location_id = self.source_location_id
        quantity = self.nett_total

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

        if not_available:
            raise ValidationError(_("There's not enough quantity of:\n%s" % '\n'.join(list(set(not_available)))))

        StockMove = self.env['stock.move']
        move_values = [self._prepare_stock_move_values(self.source_location_id, self.destination_location_id)]
        return StockMove.create(move_values)

    def _create_processing_move(self):
        self.ensure_one()

        not_available = []
        availability = {}
        Quant = self.env['stock.quant']
        
        location_id = self.processing_location_id

        for inp in self.production_record_input_ids:
            product_id = inp.product_id
            quantity = inp.quantity

            taken_qty = availability.get(product_id.id, {}).get(location_id, 0.0)
            available_qty = Quant._get_available_quantity(product_id, location_id) - taken_qty
            if quantity > available_qty:
                not_available += [_('- %s on %s' % (inp.product_id.display_name, location_id.display_name))]

            if product_id.id not in availability:
                availability[product_id.id] = {location_id.id: quantity}
            else:
                if location_id.id not in availability[product_id.id]:
                    availability[product_id.id][location_id.id] = quantity
                else:
                    availability[product_id.id][location_id.id] += quantity

        if not_available:
            raise ValidationError(_("There's not enough quantity of:\n%s" % '\n'.join(list(set(not_available)))))

        StockMove = self.env['stock.move']
        processing_location = self.processing_location_id
        move_values = []
        for inp in self.production_record_input_ids:
            production_location = inp.product_id.with_company(self.company_id).property_stock_production
            move_values += [self._prepare_stock_move_values(processing_location, production_location, product_id=inp.product_id.id, qty=inp.quantity, uom=inp.uom_id, input_id=inp)]
        for out in self.production_record_output_ids:
            production_location = out.product_id.with_company(self.company_id).property_stock_production
            move_values += [self._prepare_stock_move_values(production_location, processing_location, product_id=out.product_id.id, qty=out.quantity, uom=out.uom_id, output_id=out)]
        return StockMove.create(move_values)

    def action_confirm(self):
        self.ensure_one()
        if not hasattr(self, '_create_%s_move' % self.selected_operation_type):
            return
        moves = getattr(self, '_create_%s_move' % self.selected_operation_type)()
        moves._action_done()
        self.state = 'confirmed'

    @api.onchange('selected_operation_type')
    def _onchange_operation_type(self):
        daily_production_id = self.daily_production_id

        self.mining_site_id = daily_production_id.mining_site_id.id
        self.company_id = daily_production_id.company_id.id
        self.branch_id = daily_production_id.branch_id.id
        self.prod_rec_date = daily_production_id.date

        operation_id = daily_production_id.mining_operation_id
        operation_uom_id = operation_id and operation_id.uom_id.id or False

        self.mining_operation_id = operation_id.id

        self.gross_uom_id = operation_uom_id
        self.tare_uom_id = operation_uom_id
        self.nett_uom_id = operation_uom_id

        self.input_uom_id = operation_uom_id
        self.output_uom_id = operation_uom_id
        self.loss_uom_id = operation_uom_id
            
        if self.selected_operation_type == 'processing':
            self.production_record_input_ids = [(5,)] + [(0, 0, {
                'product_id': inp.product_id.id,
                'quantity': inp.qty,
                'uom_id': inp.uom_id.id
            }) for inp in operation_id.input_line_ids]

            self.production_record_output_ids = [(5,)] + [(0, 0, {
                'product_id': out.product_id.id,
                'quantity': out.qty,
                'uom_id': out.uom_id.id
            }) for out in operation_id.output_line_ids]

    @api.onchange('mining_operation_id')
    def _onchange_mining_operation_id(self):
        if self.mining_operation_id:
            if self.selected_operation_type == 'processing':
                self.processing_location_id = self.mining_operation_id.location_id.id
            elif self.selected_operation_type in ('extraction', 'waste_removal', 'hauling'):
                self.product_id = self.mining_operation_id.line_ids.filtered(lambda l: l.primary).product_id.id

    @api.onchange('gross_total', 'tare_total')
    def _onchange_nett_total(self):
        self.nett_total = self.gross_total - self.tare_total

    @api.onchange('input_total', 'output_total')
    def _onchange_loss_total(self):
        self.loss_total = self.input_total - self.output_total

    @api.onchange('prod_rec_date')
    def _check_prod_rec_dates(self):
        for record in self:
            if record.selected_operation_type in ['extraction', 'waste_removal', 'hauling', 'processing']:
                continue
            if record.prod_rec_date:
                if record.prod_rec_date < record.daily_production_id.start_date or \
                        record.prod_rec_date > record.daily_production_id.end_date:
                    raise ValidationError("Please select date within range!")

    @api.onchange('mining_pit_id', 'selected_operation_type')
    def _onchange_mining_pit_id(self):
        if self.selected_operation_type in ('extraction', 'waste_removal') and self.mining_pit_id:
            self.source_location_id = self.mining_pit_id.location_id and self.mining_pit_id.location_id.id or False

    @api.depends('production_record_input_ids.quantity')
    def _compute_input_totals(self):
        for record in self:
            record.input_total = sum(record.production_record_input_ids.mapped('quantity'))

    @api.depends('production_record_output_ids.quantity')
    def _compute_output_totals(self):
        for record in self:
            record.output_total = sum(record.production_record_output_ids.mapped('quantity'))

    def _prepare_stock_move_values(self, location_src_id, location_dest_id, product_id=None, qty=None, uom=None, input_id=None, output_id=None):
        self.ensure_one()
        values = {
            'name': self.name,
            'origin': self.name,
            'product_id': product_id is None and self.product_id.id or product_id,
            'product_uom': uom is None and self.product_id.uom_id.id or uom.id,
            'date': self.prod_rec_date,
            'product_uom_qty': qty is None and self.nett_total or qty,
            'quantity_done': qty is None and self.nett_total or qty,
            'location_id': location_src_id.id,
            'location_dest_id': location_dest_id.id,
            'mining_production_record_id': self.id,
            'mining_production_order_id': self.daily_production_id.id
        }
        if input_id:
            values['mining_input_id'] = input_id.id
        if output_id:
            values['mining_output_id'] = output_id.id
        return values

    def action_view_stock_moves(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('stock.stock_move_action')
        records = self.stock_move_ids
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


class MiningPorductionReordLineInput(models.Model):
    _name = 'mining.production.record.line.input'
    _description = 'Mining Production Record Line Input'
    _order = 'id desc'

    production_record_input_id = fields.Many2one('mining.production.record', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("Input Quantity should be greater than zero.")


class MiningPorductionReordLineOutput(models.Model):
    _name = 'mining.production.record.line.output'
    _description = 'Mining Production Record Line Output'
    _order = 'id desc'

    production_record_output_id = fields.Many2one('mining.production.record', ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("Output Quantity should be greater than zero.")
