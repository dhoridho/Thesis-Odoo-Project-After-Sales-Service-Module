from odoo import models, fields, api, _, tools
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.addons.equip3_mining_operations.models.mining_operations_two import OPERATION_TYPES
from odoo.exceptions import ValidationError, UserError


class MiningProductionActualization(models.Model):
    _name = 'mining.production.actualization'
    _description = 'Production Actualization'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mining.production.actualization', sequence_date=None) or _('New')
        return super(MiningProductionActualization, self).create(vals)

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.mining_production_act:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mining.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mpa')
        ], limit=1).id

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = [(5,)]
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'mpa_id': record.id,
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
    
    def _compute_moves(self):
        stock_move = self.env['stock.move']
        for record in self:
            pickings = record._get_pickings()
            picking_move_ids = pickings.mapped('move_ids_without_package')
            record.moves_count = stock_move.search_count([
                ('mining_prod_act_id', '=', record.id),
                ('id', 'not in', picking_move_ids.ids)
            ])

    def _compute_pickings(self):
        for record in self:
            record.picking_count = len(record._get_pickings())

    def _get_pickings(self):
        self.ensure_one()
        pickings = self.env['stock.picking']
        if not self.delivery_ids:
            return pickings
        if not self.delivery_ids.history_ids:
            return pickings
        if not self.delivery_ids.history_ids.iteration_ids:
            return pickings
        return self.delivery_ids.history_ids.iteration_ids.mapped('picking_id')

    def _compute_fuel_logs(self):
        fuel_logs = self.env['maintenance.fuel.logs']
        for record in self:
            record.logs_count = fuel_logs.search_count([('mining_prod_act_id', '=', record.id)])

    def _compute_all_pickings(self):
        for record in self:
            record.all_picking_done = True
            pickings = record._get_pickings()
            record.all_picking_done = all(picking.state == 'done' for picking in pickings)

    priority = fields.Selection(PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=_('New'), tracking=True)
    
    mining_prod_plan_id = fields.Many2one('mining.production.plan', string='Production Plan', readonly=True)
    mining_prod_line_id = fields.Many2one('mining.production.line', string='Production Line', readonly=True)

    mining_site_id = fields.Many2one('mining.site.control', string='Mining Site Name', required=True, readonly=True)
    mining_project_id = fields.Many2one('mining.project.control', domain="[('mining_site_id', '=', mining_site_id)]", string='Mining Pit', required=True, readonly=True)
    
    period_from = fields.Date(string='Period', required=True, tracking=True)
    period_to = fields.Date(string='Period End', required=True, tracking=True)

    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, readonly=True)
    operation_type = fields.Selection(selection=OPERATION_TYPES, string='Operation Type')
    ppic_id = fields.Many2one('res.users', string='PPIC', default=lambda self: self.env.user, required=True, readonly=True)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, readonly=True)
    analytic_group_ids = fields.Many2many('account.analytic.tag',  string="Analytic Group", readonly=True)

    approval_matrix_id = fields.Many2one(
        comodel_name='mining.approval.matrix', 
        domain="[('matrix_type', '=', 'mpa')]",
        string='Approval Matrix', 
        default=_default_approval_matrix,
        readonly=True)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mining.approval.matrix.entry',
        inverse_name='mpa_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    is_matrix_on = fields.Boolean(related='company_id.mining_production_act')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
    ], string='State', default='draft', tracking=True)

    worker_type = fields.Selection(
        selection=[
            ('with_group', 'With Group'), 
            ('without_group', 'Without Group')
        ], default='with_group', string='Worker Type')
    worker_ids = fields.Many2many(comodel_name='hr.employee', string='Worker')
    worker_group_id = fields.Many2one(comodel_name='mining.worker.group', string='Worker')

    assets_ids = fields.One2many(comodel_name='mining.production.plan.assets', inverse_name='mining_prod_act_id', string='Mining Production Actualization Assets')
    input_ids = fields.One2many(comodel_name='mining.production.plan.input', inverse_name='mining_prod_act_id', string='Mining Production Actualization Input')
    output_ids = fields.One2many(comodel_name='mining.production.plan.output', inverse_name='mining_prod_act_id', string='Mining Production Actualization Output')
    fuel_ids = fields.One2many(comodel_name='mining.production.plan.fuel', inverse_name='mining_prod_act_id', string='Mining Production Actualization Fuel')
    delivery_ids = fields.One2many(comodel_name='mining.production.plan.delivery', inverse_name='mining_prod_act_id', string='Mining Production Actualization Delivery')

    moves_count = fields.Integer(compute=_compute_moves)
    logs_count = fields.Integer(compute=_compute_fuel_logs)

    picking_count = fields.Integer(compute=_compute_pickings)
    all_picking_done = fields.Boolean(compute=_compute_all_pickings)
    
    is_bills = fields.Boolean(string='Is Bills?', default=False)

    # technical fields
    state_1 = fields.Selection(related='state', tracking=False, string='State 1')

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        if not self.company_id or not self.branch_id:
            self.approval_matrix_id = False
            return
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    @api.onchange('operation_id')
    def _onchange_operation_type(self):
        self.operation_type = False
        if self.operation_id:
            self.operation_type = self.operation_id.operation_type_id

    @api.onchange('worker_type')
    def _onchange_worker_type(self):
        if self.worker_type != 'with_gruop':
            self.worker_group_id = False

    @api.onchange('worker_group_id')
    def _onchange_worker_group_id(self):
        if self.worker_type != 'with_group':
            worker_ids = [(5,)]
        else:
            worker_ids = []
            if self.worker_group_id:
                worker_ids = self.worker_group_id.worker_ids.ids
        self.worker_ids = [(6, 0, worker_ids)]

    @api.onchange('worker_ids')
    def _onchange_worker_ids(self):
        self.assets_ids.update({'worker_ids': [(6, 0, self.worker_ids.ids)]})

    def _assign_valuations(self):

        def update(act, svl, mining_type):
            svl.write({
                'mining_prod_plan_id': act.mining_prod_plan_id and act.mining_prod_plan_id.id or False,
                'mining_prod_line_id': act.mining_prod_line_id and act.mining_prod_line_id.id or False,
                'mining_prod_act_id': act.id,
                'mining_type': mining_type
            })

        for mpa in self.search([]):
            for input_id in mpa.input_ids:
                svl_ids = input_id.move_ids.stock_valuation_layer_ids
                update(mpa, svl_ids, 'input')
            for output_id in mpa.output_ids:
                svl_ids = output_id.move_ids.stock_valuation_layer_ids
                update(mpa, svl_ids, 'output')
            for delivery_id in mpa.delivery_ids:
                svl_ids = delivery_id.move_ids.stock_valuation_layer_ids
                update(mpa, svl_ids, 'shipment')
            for fuel_id in mpa.fuel_ids:
                svl_ids = fuel_id.move_ids.stock_valuation_layer_ids
                update(mpa, svl_ids, 'fuel')

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.mining_production_act_wa_notif
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'to_be_approved'})

        if self.env.context.get('pop_back', False):
            return self.mining_prod_line_id.pop_actualization(self.id)

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})
            record.set_asset_hour_meter()
            record.set_fuel_logs()

        if self.env.context.get('pop_back', False):
            return self.mining_prod_line_id.pop_actualization(self.id)

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})

        if self.env.context.get('pop_back', False):
            return self.mining_prod_line_id.pop_actualization(self.id)

    def action_toggle_matrix(self, is_on):
        matrix = self.env['mining.approval.matrix']
        valid_state = is_on and 'draft' or 'to_be_approved'
        for record in self:
            if record.state != valid_state:
                continue
            matrix.toggle_on_off(record, is_on)
            if is_on:
                continue
            record.write({'state': 'draft'})

    def set_asset_hour_meter(self):
        self.ensure_one()
        today = fields.Date.today()
        for asset in self.assets_ids:
            self.env['maintenance.hour.meter'].create({
                'date': today,
                'maintenance_asset': asset.assets_id.id,
                'value': asset.duration
            })

    def set_fuel_logs(self):
        self.ensure_one()
        now = fields.Datetime.now()

        prod_conf_id = self.env['mining.production.conf'].search([
            ('site_id', '=', self.mining_site_id.id),
            ('operation_id', '=', self.operation_id.id)
        ], limit=1)

        if not prod_conf_id:
            return

        if self.operation_id.operation_type_id == 'shipment':
            location_id = prod_conf_id.location_dest_id
        else:
            location_id = prod_conf_id.location_id

        for fuel in self.fuel_ids:
            if not fuel.asset_id.vehicle_checkbox:
                continue

            product_id = fuel.product_id
            log_id = self.env['maintenance.fuel.logs'].create({
                'mining_prod_act_id': self.id,
                'mining_fuel_id': fuel.id,
                'vehicle': fuel.asset_id.id,
                'date': now,
                'refueling_schema': 'fuel_stock',
                'location_id': location_id.id,
                'location_dest_id': product_id.with_company(self.company_id).property_stock_production.id,
                'fuel_type': product_id.id,
                'liter': fuel.qty_done,
                'total_price': 1.0
            })
            log_id.action_confirm()

    def _validate_fuel_moves(self):
        self.ensure_one()
        prod_plan_id = self.mining_prod_plan_id and self.mining_prod_plan_id.id or False
        prod_line_id = self.mining_prod_line_id and self.mining_prod_line_id.id or False

        logs = self.env['maintenance.fuel.logs'].search([('mining_fuel_id', 'in', self.fuel_ids.ids)])
        moves = self.env['stock.move']
        for fuel in self.fuel_ids:
            fuel_logs = logs.filtered(lambda l: l.mining_fuel_id == fuel)
            picking_ids = self.env['stock.picking'].search([('fuel_log_id', 'in', fuel_logs.ids)])
            for picking in picking_ids:
                picking.action_confirm()
                picking.button_validate()
                for move in picking.move_ids_without_package:
                    move.write({
                        'mining_prod_plan_id': prod_plan_id,
                        'mining_prod_line_id': prod_line_id,
                        'mining_prod_act_id': self.id,
                        'mining_operation_id': self.operation_id.id,
                        'mining_fuel_id': fuel.id,
                    })
            moves |= picking_ids.mapped('move_ids_without_package')
        return moves

    def _prepare_shipment_values(self):
        self.ensure_one()
        prod_plan_id = self.mining_prod_plan_id and self.mining_prod_plan_id.id or False
        prod_line_id = self.mining_prod_line_id and self.mining_prod_line_id.id or False
        now = fields.Datetime.now()
        values = []
        for delivery in self.delivery_ids:
            history_ids = delivery.history_ids.filtered(lambda h: h.mining_prod_act_id == self)

            if not history_ids:
                continue

            for line in history_ids[0].iteration_ids:
                product_id = line.product_id
                move_vals = {
                    'mining_prod_plan_id': prod_plan_id,
                    'mining_prod_line_id': prod_line_id,
                    'mining_prod_act_id': self.id,
                    'mining_operation_id': self.operation_id.id,
                    'mining_delivery_id': delivery.id,
                    'name': self.name,
                    'date': now,
                    'product_id': product_id.id,
                    'product_uom_qty': line.amount,
                    'product_uom': line.uom_id.id,
                    'quantity_done': line.amount,
                    'location_id': line.location_src_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'company_id': self.company_id.id,
                    'price_unit': product_id.standard_price,
                    'origin': self.name,
                    'state': 'draft',
                    'warehouse_id': line.location_src_id.get_warehouse().id
                }
                values += [move_vals]
        return values

    def _prepare_extraction_values(self):
        self.ensure_one()
        prod_plan_id = self.mining_prod_plan_id and self.mining_prod_plan_id.id or False
        prod_line_id = self.mining_prod_line_id and self.mining_prod_line_id.id or False
        conf_id = self.env['mining.production.conf'].search([
            ('site_id', '=', self.mining_site_id.id),
            ('operation_id', '=', self.operation_id.id)
        ], limit=1)
        location_id = conf_id.location_id
        warehouse_id = location_id.get_warehouse()
        warehouse_id = warehouse_id and warehouse_id.id or False
        values = []
        for line in self.output_ids:
            product_id = line.product_id
            move_vals = {
                'mining_prod_plan_id': prod_plan_id,
                'mining_prod_line_id': prod_line_id,
                'mining_prod_act_id': self.id,
                'mining_operation_id': self.operation_id.id,
                'mining_output_id': line.id,
                'name': self.name,
                'date': self.period_from,
                'date_deadline': self.period_to,
                'product_id': product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': line.uom_id.id,
                'quantity_done': line.qty_done,
                'location_id': product_id.with_company(self.company_id).property_stock_production.id,
                'location_dest_id': location_id.id,
                'company_id': self.company_id.id,
                'price_unit': product_id.standard_price,
                'origin': self.name,
                'state': 'draft',
                'warehouse_id': warehouse_id
            }
            values += [move_vals]
        return values

    def _prepare_production_values(self):
        self.ensure_one()
        prod_plan_id = self.mining_prod_plan_id and self.mining_prod_plan_id.id or False
        prod_line_id = self.mining_prod_line_id and self.mining_prod_line_id.id or False

        def _prepare(lines, key, location_src_id, location_dest_id):
            
            values = []
            for line in lines:
                product_id = line.product_id
                virtual_location_id = product_id.with_company(self.company_id).property_stock_production

                if not location_src_id:
                    location_src_id = virtual_location_id
                elif not location_dest_id:
                    location_dest_id = virtual_location_id

                warehouse_id = location_src_id.get_warehouse()
                warehouse_id = warehouse_id and warehouse_id.id or False

                move_vals = {
                    'mining_prod_plan_id': prod_plan_id,
                    'mining_prod_line_id': prod_line_id,
                    'mining_prod_act_id': self.id,
                    'mining_operation_id': self.operation_id.id,
                    key: line.id,
                    'name': self.name,
                    'date': self.period_from,
                    'date_deadline': self.period_to,
                    'product_id': product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.uom_id.id,
                    'quantity_done': line.qty_done,
                    'location_id': location_src_id.id,
                    'location_dest_id': location_dest_id.id,
                    'company_id': self.company_id.id,
                    'price_unit': product_id.standard_price,
                    'origin': self.name,
                    'state': 'draft',
                    'warehouse_id': warehouse_id
                }
                values += [move_vals]
            return values

        conf_id = self.env['mining.production.conf'].search([
            ('site_id', '=', self.mining_site_id.id),
            ('operation_id', '=', self.operation_id.id)
        ], limit=1)

        input_values = _prepare(self.input_ids, 'mining_input_id', conf_id.location_id, False)
        output_values = _prepare(self.output_ids, 'mining_output_id', False, conf_id.location_id)
        return input_values + output_values
    
    def _update_jurnal(self, account_move_id, fuel_move_id, account_type):
        jurnal_data = self.env['account.move.line'].search([('move_id', '=', account_move_id)])
        jurnal_fuel_data = self.env['account.move.line'].search([('move_id', '=', fuel_move_id)], limit=1)
        if jurnal_fuel_data:
            # [0] for credit / [1] for debit
            jurnal_data[account_type].write({
                'name': jurnal_fuel_data.name,
                'account_id': jurnal_fuel_data.account_id.id
            })

    def _prepare_move_vals(self, current_stock_valuation, input_stock_valuation = 0, fuel_stock_valution = 0):
        self.ensure_one()
        product_ids = current_stock_valuation.mapped('product_id')

        if not product_ids:
            raise ValidationError(_("There's no valuations!"))

        journal_id = False
        products = []
        for product_id in product_ids:
            if product_id.categ_id.property_stock_journal:
                journal_id = product_id.categ_id.property_stock_journal
                break
            products.append('- %s' % product_id.display_name)
        products = '\n'.join(products)

        fuel_journal_id = 0
        if fuel_stock_valution:
            fuel_journal_id = self.env['account.move'].search([('id', '=', fuel_stock_valution)]).journal_id.id
        else:
            fuel_journal_id = journal_id.id

        if not journal_id:
            raise ValidationError(_('You have to set Stock Journal for any of these products first!\n%s' % products))

        line_ids = []
        for line in current_stock_valuation:
            if line.product_id.categ_id.property_valuation != 'real_time':
                raise ValidationError(_('Set category of product %s to Automated first!' % line.product_id.display_name))

            account_id = line.product_id.categ_id.property_stock_valuation_account_id.id
            name = '%s-  %s' % (self.name, line.product_id.display_name)
            if input_stock_valuation == 0:
                line_ids += [
                    (0, 0, {
                        'account_id': account_id,
                        'name': name,
                        'debit': 0.0,
                        'credit': abs(line.value),
                    }),
                    (0, 0, {
                        'account_id': account_id,
                        'name':  name,
                        'debit': abs(line.value),
                        'credit': 0.0,
                    })
                ]
            else:
                # set input and output jurnal entry line
                line_ids += [
                    (0, 0, {
                        'account_id': current_stock_valuation.account_move_id.line_ids[0].account_id.id,
                        'name':  current_stock_valuation.account_move_id.line_ids[0].name,
                        'debit': 0.0,
                        'credit':  current_stock_valuation.account_move_id.line_ids[0].credit,
                    }),(0, 0, {
                        'account_id': current_stock_valuation.account_move_id.line_ids[1].account_id.id,
                        'name': current_stock_valuation.account_move_id.line_ids[1].name,
                        'debit': current_stock_valuation.account_move_id.line_ids[1].debit,
                        'credit': 0.0,
                    })
                ]
                
                line_ids += [
                    (0, 0, {
                        'account_id': input_stock_valuation.line_ids[0].account_id.id,
                        'name': input_stock_valuation.line_ids[0].name,
                        'debit': 0.0,
                        'credit': input_stock_valuation.line_ids[0].credit,
                    }),
                    (0, 0, {
                        'account_id': input_stock_valuation.line_ids[1].account_id.id,
                        'name':  input_stock_valuation.line_ids[1].name,
                        'debit': input_stock_valuation.line_ids[1].debit,
                        'credit': 0.0,
                    }),
                ]
        
        values = {
            'ref': name,
            'date': fields.Datetime.now(),
            'discount_type': 'global',
            'journal_id': fuel_journal_id if journal_id.id != fuel_journal_id else journal_id.id,
            'line_ids': line_ids
        }
        
        return values


    def _get_fuel_input_value(self, fuel_id = 0, input_id = 0):
        input_value = 0
        fuel_value  = 0
        if fuel_id:
            fuel_value = self.env['stock.valuation.layer'].search([('stock_move_id', '=', fuel_id)]).value
        if input_id:
            input_value = self.env['stock.valuation.layer'].search([('stock_move_id', '=', input_id)]).value
        return abs(fuel_value) + abs(input_value)

    def _is_in(self, location_id, location_dest_id):
        return not location_id._should_be_valued() and location_dest_id._should_be_valued()

    def _is_out(self, location_id, location_dest_id):
        return location_id._should_be_valued() and not location_dest_id._should_be_valued()

    def _is_dropshipped(self, location_id, location_dest_id):
        return location_id.usage == 'supplier' and location_dest_id.usage == 'customer'

    def _is_dropshipped_returned(self, location_id, location_dest_id):
        return location_id.usage == 'customer' and location_dest_id.usage == 'supplier'
        
    def _action_confirm(self, skip_check=False):
        self.ensure_one()

        # private method of action_confirm
        operation_type = self.operation_id.operation_type_id
        if operation_type == 'shipment':
            move_values = []
        elif operation_type == 'extraction':
            move_values = self._prepare_extraction_values()
        else:
            move_values = self._prepare_production_values()

        if not skip_check and move_values:
            not_valuated = []
            for values in move_values:
                location_id = self.env['stock.location'].browse(values['location_id'])
                location_dest_id = self.env['stock.location'].browse(values['location_dest_id'])
                if not any(getattr(self, '_is_%s' % valued_type)(location_id, location_dest_id) 
                    for valued_type in ('in', 'out', 'dropshipped', 'dropshipped_returned')):
                        not_valuated += ['- %s To %s' % (location_id.display_name, location_dest_id.display_name)]
            if not_valuated:
                context = {
                    'default_mining_prod_act_id': self.id,
                    'default_message': '\n'.join(not_valuated),
                    'pop_back': self.env.context.get('pop_back', False)
                }
                return {
                    'name': _('Confirmation'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'action.actualization.confirm',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': context
                }

        total_qty = 0
        fuel_value = 0
        input_account_id = 0
        fuel_account_move_id = 0
        fuel_stock_id = 0
        input_stock_id = 0

        fuel_move_ids = self._validate_fuel_moves()
        for fuel in fuel_move_ids:
            fuel.stock_valuation_layer_ids.write({
                'mining_prod_plan_id': self.mining_prod_plan_id and self.mining_prod_plan_id.id,
                'mining_prod_line_id': self.mining_prod_line_id.id,
                'mining_prod_act_id': self.id,
                'mining_type': 'fuel'
            })

            if fuel.stock_valuation_layer_ids.mining_type == 'fuel':
                fuel_value = fuel.stock_valuation_layer_ids.value
                fuel_stock_id = fuel.stock_valuation_layer_ids.stock_move_id.id
                fuel_account_move_id = fuel.stock_valuation_layer_ids.account_move_id.id
        
        if operation_type == 'shipment':
            pickings = self._get_pickings()
            move_ids = pickings.mapped('move_ids_without_package')
        else:
            for value in move_values:
                if value['quantity_done'] and value['product_uom_qty'] > 1:
                    # save qty for later
                    total_qty = value['quantity_done']
                    
                if operation_type == 'production':
                    if 'mining_input_id' in value:
                        temp_value = 0
                        temp_value = value['price_unit']
                    if 'mining_output_id' in value:
                        value.update({'price_unit': fuel_value if fuel_value != 0 else temp_value})

                elif operation_type == 'extraction' or operation_type == 'shipment':
                    value.update({'price_unit': fuel_value})
            move_ids = self.env['stock.move'].create(move_values)
            move_ids._action_done()

        for move in move_ids:
            mining_type = False
            if move.mining_input_id.id:
                mining_type = 'input'
            elif move.mining_output_id.id:
                mining_type = 'output'
            elif move.mining_delivery_id.id:
                mining_type = 'shipment'
            
            move.stock_valuation_layer_ids.write({
                'mining_prod_plan_id': self.mining_prod_plan_id and self.mining_prod_plan_id.id,
                'mining_prod_line_id': self.mining_prod_line_id.id,
                'mining_prod_act_id': self.id,
                'mining_type': mining_type,
            })

            if move.stock_valuation_layer_ids.mining_type != 'fuel' and\
                move.stock_valuation_layer_ids.mining_type != False:
                if move.stock_valuation_layer_ids.value > 0 and\
                   move.stock_valuation_layer_ids.mining_type == 'output':
                        move.stock_valuation_layer_ids.value = self._get_fuel_input_value(fuel_stock_id, input_stock_id)
                        move.stock_valuation_layer_ids.unit_cost = self._get_fuel_input_value(fuel_stock_id, input_stock_id)
                        move.stock_valuation_layer_ids.remaining_value = self._get_fuel_input_value(fuel_stock_id, input_stock_id)
                        move.stock_valuation_layer_ids.quantity = total_qty if total_qty != 0 else 1

                        if fuel_account_move_id != 0 and input_account_id != 0:
                            self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id,\
                                            fuel_account_move_id, 0)
                            self._update_jurnal(input_account_id,\
                                            fuel_account_move_id, 1)

                        if input_account_id != 0 and fuel_account_move_id == 0:
                            self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id, \
                                                input_account_id, 0)

                        if input_account_id == 0 and fuel_account_move_id != 0:
                            self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id, \
                                                fuel_account_move_id, 0)

                        if fuel_account_move_id != 0 and input_account_id != 0:
                            # re-create both output and input jurnal entry
                            input_je = self.env['account.move'].search([('id', '=', input_account_id)])
                            values = self._prepare_move_vals(move.stock_valuation_layer_ids, input_je)
                            account_move_id = self.env['account.move'].create(values)
                            account_move_id.action_post()
                            # update account_move_id in previous stock_valuation_layer
                            move.stock_valuation_layer_ids.account_move_id = account_move_id.id

                elif move.stock_valuation_layer_ids.value < 0 and\
                     move.stock_valuation_layer_ids.mining_type == 'input':
                        # update account_move_id in previous stock_valuation_layer
                        input_account_id = move.stock_valuation_layer_ids.account_move_id.id
                        input_stock_id = move.stock_valuation_layer_ids.stock_move_id.id

            if move.stock_valuation_layer_ids.mining_type != 'fuel' and\
                move.stock_valuation_layer_ids.mining_type == False:
                move.stock_valuation_layer_ids.value = self._get_fuel_input_value(fuel_stock_id, input_stock_id)
                
            if move.stock_valuation_layer_ids.value == 0 and\
                move.stock_valuation_layer_ids.mining_type == 'output':
                move.stock_valuation_layer_ids.value = self._get_fuel_input_value(fuel_stock_id, input_stock_id)
                values = self._prepare_move_vals(move.stock_valuation_layer_ids)
                account_move_id = self.env['account.move'].create(values)
                account_move_id.action_post()
                # update account_move_id in previous stock_valuation_layer
                move.stock_valuation_layer_ids.account_move_id = account_move_id.id

                if fuel_account_move_id == 0:
                    self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id,\
                                        input_account_id, 0)
                elif input_account_id == 0:
                    self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id,\
                                        fuel_account_move_id, 0)

            if move.stock_valuation_layer_ids.mining_type == False\
                and move.mining_delivery_id.id:
                shipment_data = self.env['stock.move'].search([('mining_delivery_id', '=', move.mining_delivery_id.id)])
                move.stock_valuation_layer_ids = [(0, 0, {
                    'mining_prod_plan_id': shipment_data.mining_prod_plan_id.id,
                    'mining_prod_line_id': shipment_data.mining_prod_line_id.id ,
                    'mining_prod_act_id':  shipment_data.mining_prod_act_id.id,
                    'company_id': shipment_data.company_id.id,
                    'product_id': shipment_data.product_id.id,
                    'mining_type': mining_type,
                    'value': self._get_fuel_input_value(fuel_stock_id),
                    'quantity': shipment_data.product_qty
                })]

                values = self._prepare_move_vals(move.stock_valuation_layer_ids)
                account_move_id = self.env['account.move'].create(values)
                account_move_id.action_post()
                # update account_move_id in previous stock_valuation_layer
                move.stock_valuation_layer_ids.account_move_id = account_move_id.id
                if fuel_account_move_id != 0:
                    self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id,\
                                            fuel_account_move_id, 0)

            if move.stock_valuation_layer_ids.mining_type == False\
                and move.mining_output_id.id:
                output_data = self.env['stock.move'].search([('mining_output_id', '=', move.mining_output_id.id)])
                move.stock_valuation_layer_ids = [(0, 0, {
                    'mining_prod_plan_id': output_data.mining_prod_plan_id.id,
                    'mining_prod_line_id': output_data.mining_prod_line_id.id ,
                    'mining_prod_act_id':  output_data.mining_prod_act_id.id,
                    'company_id': output_data.company_id.id,
                    'product_id': output_data.product_id.id,
                    'mining_type': mining_type,
                    'unit_cost': self._get_fuel_input_value(fuel_stock_id),
                    'remaining_value': self._get_fuel_input_value(fuel_stock_id),
                    'value': self._get_fuel_input_value(fuel_stock_id)
                })]

                values = self._prepare_move_vals(move.stock_valuation_layer_ids, fuel_stock_valution=fuel_account_move_id)
                account_move_id = self.env['account.move'].create(values)
                account_move_id.action_post()
                # update account_move_id in previous stock_valuation_layer
                move.stock_valuation_layer_ids.account_move_id = account_move_id.id
                if fuel_account_move_id != 0:
                    self._update_jurnal(move.stock_valuation_layer_ids.account_move_id.id,\
                                            fuel_account_move_id, 0)
        self.state = 'confirm'


    def action_confirm(self, skip_check=False):
        self.ensure_one()

        for rec in self.assets_ids:
            print(rec.assets_id.state)
            if(rec.assets_id.state != 'operative'):
                raise UserError(_("The asset %s is currently non operative.") % (rec.assets_id.name))
        
        if not self.is_matrix_on and not skip_check:
            self.set_asset_hour_meter()
            self.set_fuel_logs()

        action = self._action_confirm(skip_check=skip_check)
        if action:
            return action

        if self.env.context.get('pop_back', False):
            return self.mining_prod_line_id.pop_actualization(self.id)

    def action_view_moves(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('stock.stock_move_action')
        records = self.env['stock.move'].search([('mining_prod_act_id', '=', self.id)])
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

    def action_view_fuel_logs(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('equip3_asset_fms_masterdata.maintenance_fuel_logs_action')
        records = self.env['maintenance.fuel.logs'].search([('mining_prod_act_id', '=', self.id)])
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('equip3_asset_fms_masterdata.maintenance_fuel_logs_view_form').id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context') or '{}', self._context), create=False))
        return result

    def action_view_pickings(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_delivery_order')
        records = self._get_pickings()
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context') or '{}', self._context), create=False))
        return result