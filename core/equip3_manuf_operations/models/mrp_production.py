from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.tools import format_datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.addons.mrp.models.mrp_production import MrpProduction as BasicMrpProduction


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # OVERRIDE METHODS & FIELDS
    # ==================================================================================================================
    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)
    product_id = fields.Many2one('product.product', string='Product', tracking=True)
    date_start = fields.Datetime('Actual Date', copy=False, index=True, readonly=True)
    state = fields.Selection(selection_add=[
        ('approval', 'To be Approved'),
        ('approved', 'Approved'),
        ('reject', 'Rejected'),
        ('confirmed',)
        ],
        string='State',
        compute='_compute_state',
        copy=False,
        index=True,
        readonly=True,
        store=True,
        tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * Approval: The MO is To be Approved.\n"
             " * Approved: The MO is Approved.\n"
             " * Reject: The MO is To be Rejected.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")

    bom_id = fields.Many2one('mrp.bom', domain="""[
        ('type', '=', 'normal'),
        ('equip_bom_type', '=', 'mrp'),
        '|',
            ('branch_id', '=', False),
            ('branch_id', '=', branch_id),
        '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id)]""")
    
    qty_producing = fields.Float(string="Quantity Producing")
    is_mr_created = fields.Boolean('Is Material Request Created', default=False)

    def _register_hook(self):
        BasicMrpProduction._patch_method('action_confirm', action_confirm)
        BasicMrpProduction._patch_method('_create_workorder', _create_workorder)
        BasicMrpProduction._patch_method('_get_moves_finished_values', _get_moves_finished_values)
        return super(MrpProduction, self)._register_hook()

    def _unregister_hook(self):
        BasicMrpProduction._revert_method('action_confirm')
        BasicMrpProduction._revert_method('_create_workorder')
        BasicMrpProduction._revert_method('_get_moves_finished_values')
        return super(MrpProduction, self)._unregister_hook()

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        res = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)
        res['mrp_plan_id'] = self.mrp_plan_id and self.mrp_plan_id.id or False
        if not operation_id:
            raise ValidationError(_('Please set Consumed in Operation for material %s in BoM!' % product_id.display_name))
        operation = self.env['mrp.routing.workcenter'].browse(operation_id)
        workcenter_id = operation._get_workcenter()
        res['location_id'] = workcenter_id.location_id.id
        res['branch_id'] = self.branch_id and self.branch_id.id or False
        return res

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        if byproduct_id:
            operation_id = self.bom_id.operation_ids[-1].id
        
        res = super(MrpProduction, self)._get_move_finished_values(product_id, product_uom_qty, product_uom, operation_id, byproduct_id)
        
        finished_id = self.env.context.get('finished_id', False)
        if finished_id:
            res['finished_id'] = finished_id
        
        group_orders = self.procurement_group_id.mrp_production_ids
        move_dest_ids = self.move_dest_ids
        if len(group_orders) > 1:
            move_dest_ids |= group_orders[0].move_finished_ids.filtered(lambda m: not m.byproduct_id).move_dest_ids
        res['move_dest_ids'] = [(4, x.id) for x in move_dest_ids]

        if not byproduct_id:
            return res
        
        operation = self.env['mrp.routing.workcenter'].browse(operation_id)
        location_dest_id = res['location_dest_id']
        if not operation and self.bom_id and self.bom_id.operation_ids:
            operation = self.bom_id.operation_ids[-1]
        if operation:
            workcenter_id = operation._get_workcenter()
            res['production_byproduct_loc_id'] = workcenter_id.location_id.id
            location_dest_id = workcenter_id.location_byproduct_id.id
        res['location_dest_id'] = location_dest_id
        res['branch_id'] = self.branch_id and self.branch_id.id or False
        return res

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_move_finished(self):
        self.move_finished_ids = [(5,)] + [(0, 0, values) for values in self._get_moves_finished_values()]

    @api.depends('move_finished_ids')
    def _compute_move_byproduct_ids(self):
        for order in self:
            order.move_byproduct_ids = order.move_finished_ids.filtered(lambda m: m.byproduct_id)

    def _set_move_byproduct_ids(self):
        move_finished_ids = self.move_finished_ids.filtered(lambda m: not m.byproduct_id)
        self.move_finished_ids = move_finished_ids | self.move_byproduct_ids

    # we dont want location_id of move_raw_ids change
    # since material location now filled based workcenter.location_id
    @api.onchange('location_src_id', 'move_raw_ids', 'bom_id')
    def _onchange_location(self):
        pass
    
    # only update finished goods destination location
    # since byproduct location now filled based workcenter.location_byproduct_id
    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
    def _onchange_location_dest(self):
        destination_location = self.location_dest_id
        update_value_list = []
        for move in self.move_finished_ids.filtered(lambda m: not m.byproduct_id):
            update_value_list += [(1, move.id, ({
                'warehouse_id': destination_location.get_warehouse().id,
                'location_dest_id': destination_location.id,
            }))]
        self.move_finished_ids = update_value_list

    @api.onchange('date_planned_start', 'product_id', 'duration_expected')
    def _onchange_date_planned_start(self):
        # override
        if self.date_planned_start and not self.is_planned:
            date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
            date_planned_finished = date_planned_finished + relativedelta(days=self.company_id.manufacturing_lead)
            date_planned_finished = date_planned_finished + relativedelta(minutes=self.duration_expected)
            self.date_planned_finished = date_planned_finished
            
            self.move_raw_ids = [(1, m.id, {'date': self.date_planned_start}) for m in self.move_raw_ids]
            self.move_finished_ids = [(1, m.id, {'date': date_planned_finished}) for m in self.move_finished_ids]

    def action_confirm(self):
        for production in self:
            if production.sale_order_id or (production.mrp_plan_id and production.mrp_plan_id.sale_order_id):
                workorder_ids = production.workorder_ids.filtered(lambda wo: wo.state in ['ready', 'pending'])
                workorder_ids.leave_id.unlink()

        res = super(MrpProduction, self).action_confirm()
        
        for production in self:
            n_workorders = len(production.workorder_ids)
            for sequence, workorder in enumerate(production.workorder_ids):
                move_raw_ids = production.move_raw_ids.filtered(lambda move: move.operation_id == workorder.operation_id)
                workorder.move_raw_ids = [(6, 0, move_raw_ids.ids)]

                is_last_workorder = sequence == n_workorders - 1
                if is_last_workorder:
                    workorder.byproduct_ids = [(6, 0, production.move_byproduct_ids.ids)]
            production._plan_workorders()

        autoreserve = self.env.context.get('is_plan_autoreserve', 
        self.env.company.mo_auto_reserve_availability_materials)

        if not autoreserve:
            return res

        result = self.action_assign(fill_with_available=True)
        if not isinstance(result, dict):
            return result

        line_ids = result.get('context', {}).get('default_line_ids', [])
        wizard = self.env['mrp.reserve.material'].create({'line_ids': line_ids})
        return wizard.action_confirm()

    def button_plan(self):
        res = super(MrpProduction, self).button_plan()
        if self.mrp_plan_id:
            self.mrp_plan_id._recompute_scheduled_date()
        return res

    def button_unplan(self):
        res = super(MrpProduction, self).button_unplan()
        now = fields.Datetime.now()
        self.date_planned_start = now
        self.date_planned_finished = now + timedelta(hours=1)
        if self.mrp_plan_id:
            self.mrp_plan_id._recompute_scheduled_date()
        return res

    def _plan_workorders(self, replan=False):
        self.ensure_one()
        if not self.workorder_ids:
            return
        for workorder in self.workorder_ids:
            workorder.workcenter_id.resource_id.tz = self.env.user.tz
            workorder.workcenter_id.resource_calendar_id.tz = self.env.user.tz
        if self.child_ids:
            self.date_planned_start = max(self.child_ids.mapped('date_planned_finished'))
        return super(MrpProduction, self)._plan_workorders(replan=replan)

    def action_assign(self, fill_with_available=False):
        """ param: fill_with_available
        If it's True, will fill `to_reserve_uom_qty` on wizard with `availability_uom_qty`
        if quantity to reserve is more than available quantity (e.g. to_reserve_uom_qty > availability_uom_qty).
        Otherwise, will force `to_reserve_uom_qty` to have quantity needed for the move.
        Used in `_action_confirm` to bypass constrains when confirming wizard """

        allow_partial = self.env.context.get('is_plan_allow_partial', 
        self.env.company.mrp_production_partial_availability)

        moves = self.mapped('move_raw_ids').filtered(
            lambda m: m.state in ('assigned', 'confirmed', 'waiting', 'partially_available'))

        out_of_stocks = []
        default_lines = []
        availability = {}
        for sequence, move in enumerate(moves):
            product_id = move.product_id
            location_id = move.location_id

            available_qty = availability.get(product_id.id, {}).get(location_id.id, move._get_available_quantity(location_id))
            available_uom_qty = product_id.uom_id._compute_quantity(available_qty, move.product_uom)

            to_reserve_uom_qty = move.product_uom_qty
            if move.product_id.tracking in ('lot', 'serial') and move.mrp_reserve_line_ids:
                to_reserve_uom_qty = sum(move.mrp_reserve_line_ids.mapped('product_qty'))
            max_reserve_uom_qty = min([available_uom_qty, to_reserve_uom_qty])

            default_lines += [(0, 0, {
                'sequence': sequence,
                'move_id': move.id,
                'to_reserve_uom_qty': max_reserve_uom_qty if fill_with_available else to_reserve_uom_qty
            })]
            
            if available_uom_qty < to_reserve_uom_qty:
                out_of_stocks += [_('- %s on location %s' % (product_id.display_name, location_id.display_name))]

            to_reserve_qty = move.product_uom._compute_quantity(max_reserve_uom_qty, product_id.uom_id)
            reserved_availability = move.product_uom._compute_quantity(move.reserved_availability, product_id.uom_id)
            
            next_available_qty = available_qty - (to_reserve_qty - reserved_availability)
            if product_id.id in availability:
                availability[product_id.id][location_id.id] = next_available_qty
            else:
                availability[product_id.id] = {location_id.id: next_available_qty}

        if allow_partial:
            # create wizard first to enable button
            wizard = self.env['mrp.reserve.material'].create({'line_ids': default_lines})
            return { 
                'type': 'ir.actions.act_window',
                'name': _('Partial Reserve Material'),
                'res_model': 'mrp.reserve.material',
                'target': 'new',
                'view_mode': 'form',
                'res_id': wizard.id,
                'context': {'default_line_ids': default_lines}
            }

        if out_of_stocks:
            raise UserError(_('There is not enough stock for:\n%s\n\nPlease check material reserve settings.' % '\n'.join(out_of_stocks)))
        return super(MrpProduction, self).action_assign()

    @api.onchange('product_id', 'picking_type_id', 'company_id', 'branch_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        elif not self.bom_id or self.bom_id.product_tmpl_id != self.product_tmpl_id or (self.bom_id.product_id and self.bom_id.product_id != self.product_id) or self.bom_id.branch_id.id != self.branch_id.id:
            bom = self.env['mrp.bom'].with_context(branch_id=self.branch_id.id, equip_bom_type='mrp')._bom_find(product=self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id

    def button_unbuild(self):
        res = super(MrpProduction, self).button_unbuild()
        context = res.get('context', {})
        context.update({
            'default_branch_id': self.branch_id.id,
            'default_location_dest_id': False
        })
        res['context'] = context
        return res
        
    # NEW ADDED METHODS & FIELDS
    # ==================================================================================================================
    @api.onchange('bom_id')
    def _onchange_bom_id_for_product(self):
        product_id = False
        if self.bom_id:
            product_id = self.bom_id.product_id and self.bom_id.product_id.id or self.bom_id.product_tmpl_id.product_variant_ids[0].id
        self.product_id = product_id

    @api.onchange('branch_id')
    def _onchange_branch(self):
        (self.move_raw_ids | self.move_finished_ids).update({'branch_id': self.branch_id and self.branch_id.id or False})
    
    @api.model
    def _get_default_location_reject_id(self):
        return self._get_default_location_dest_id()

    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True)

    mrp_plan_id = fields.Many2one('mrp.plan', string='Production Plan', tracking=True)
    mrp_plan_state = fields.Selection(related='mrp_plan_id.state', string='Plan State')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, copy=False)
    rejected_location_dest_id = fields.Many2one(
        'stock.location',
        string='Rejected Products Location',
        default=_get_default_location_reject_id,
        readonly=True, required=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]},
        check_company=True,
        help="Location where the system will stock the rejected products.")

    additional_mo = fields.Boolean(string='Additional', default=False)

    parent_id = fields.Many2one('mrp.production', string='Production Ancestor')
    child_ids = fields.One2many('mrp.production', 'parent_id', string='Ancestor To')    
    mrp_force_done = fields.Boolean(related="company_id.mrp_force_done", readonly=False)
    
    allow_submit_purchase_request = fields.Boolean("Allow Submit Purchase Request", default=False)
    allow_submit_material_request = fields.Boolean("Allow Submit Material Request", default=False)
    mo_force_done = fields.Boolean(related="company_id.mo_force_done", readonly=False)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    
    bom_finished_type = fields.Selection(selection=[
        ('single', 'Singe Finished Good'),
        ('multi', 'Multiple Finished Goods')
    ], default='single', required=True)
    move_finished_only_ids = fields.One2many('stock.move', compute='_compute_move_finished_only')

    bom_operation_start_mode = fields.Selection(selection=[
        ('flexible', 'Flexible, allows operations to start immediately'),
        ('sequential', 'Sequential, the operations start one after another operation has finished'),
        ('adaptive', 'Adaptive, can start immediately with the partial output of the previous operation')
    ], string='BoM Operation Start Mode', default='sequential', required=True)

    # unused fields, may delete someday
    mrp_submit_purchase_request = fields.Boolean(string='MRP Submit Purchase Request', related="company_id.mrp_submit_purchase_request", readonly=False)
    mrp_submit_material_request = fields.Boolean(string='MRP Submit Materials Request', related="company_id.mrp_submit_material_request", readonly=False)

    @api.onchange('bom_id')
    def _set_bom_fields(self):
        self.bom_finished_type = self.bom_id.finished_type
        self.bom_operation_start_mode = self.bom_id.operation_start_mode

    @api.depends('move_finished_ids')
    def _compute_move_finished_only(self):
        for order in self:
            order.move_finished_only_ids = order.move_finished_ids.filtered(lambda o: o.finished_id)

    @api.onchange('rejected_location_dest_id')
    def _onchange_rejected_location_dest_id(self):
        self.move_finished_ids.filtered(lambda m: not m.byproduct_id).update({
            'location_rejected_id': self.rejected_location_dest_id.id
        })

    @api.onchange('workorder_ids')
    def onchange_workorder_ids(self):
        if self.workorder_ids:
            try:
                last_workorder = self.workorder_ids.sorted(key=lambda x: x.id)[-1]
            except TypeError:
                last_workorder = self.workorder_ids.sorted(key=lambda x: x._origin.id)[-1]

            self.location_dest_id = last_workorder.workcenter_id.location_finished_id.id
            self.rejected_location_dest_id = last_workorder.workcenter_id.location_rejected_id.id

    def action_set_draft(self):
        self.ensure_one()
        if self.state != 'reject' or self.is_locked:
            return
        if self.approval_matrix_id:
            self.approval_matrix_id.toggle_on_off(self, False)
            self.approval_matrix_id.toggle_on_off(self, True)
        self.state = 'draft'

    # APPROVAL MATRIX
    # ==================================================================================================================
    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.manufacturing_order_conf:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mrp.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mo')
        ], limit=1).id

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = [(5,)]
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'mo_id': record.id,
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

    is_matrix_on = fields.Boolean(related='company_id.manufacturing_order_conf')
    
    approval_matrix_id = fields.Many2one(
        comodel_name='mrp.approval.matrix', 
        domain="""[
            ('matrix_type', '=', 'mo'),
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix', 
        default=_default_approval_matrix)
    approval_matrix_line_ids = fields.One2many(
        comodel_name='mrp.approval.matrix.entry',
        inverse_name='mo_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)
    
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)
    state_no_approval_matrix = fields.Selection(related='state', string='State No Approval Matrix')

    @api.onchange('user_id', 'company_id', 'branch_id', 'product_id')
    def onchange_branch(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)
    
    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.send_wa_approval_notification_mrp
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'approval'})

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'reject'})

    # ASSIGNED LABORS
    # ==================================================================================================================
    @api.depends(
        'labor_type', 'labor_workorder_id', 'labor_group_id',
        'labor_group_id.labor_ids', 'labor_ids')
    def _compute_labor_hide_assign_button(self):
        for record in self:
            err_message = record.check_action_assign_labor()
            record.labor_hide_assign_button = err_message is not False

    labor_type = fields.Selection(
        selection=[
            ('with_group', 'With Group'),
            ('without_group', 'Without Group')
        ],
        string='Labor Type',
        default='with_group',
        required=True,
        tracking=True)
    labor_workorder_id = fields.Many2one(
        'mrp.workorder',
        string='Labor Production Work Order',
        domain="[('id', 'in', workorder_ids), ('state', 'not in', ('done', 'cancel'))]",
        tracking=True)
    labor_group_id = fields.Many2one('mrp.labor.group', string='Labor Group', tracking=True)
    labor_ids = fields.Many2many('hr.employee', string='Labor', domain="[('active', '=', True)]")
    labor_hide_assign_button = fields.Boolean(compute=_compute_labor_hide_assign_button)
    assign_ids = fields.One2many('mrp.labor.assign', 'production_id', string='Assigned Labors')

    def reset_labor_form(self):
        self.ensure_one()
        return self.write({
            'labor_type': 'with_group',
            'labor_workorder_id': False,
            'labor_group_id': False,
            'labor_ids': [(5,)]
        })

    def check_action_assign_labor(self):
        self.ensure_one()
        err_message = False
        if not self.labor_workorder_id:
            err_message = _('Please select Production Work Order to assign!')

        if self.labor_type == 'with_group':
            if not self.labor_group_id:
                err_message = _('Please select Labor Group to assign!')
            elif not self.labor_group_id.labor_ids:
                err_message = _('The selected labor group has no employees to assign!')
        else:
            if not self.labor_ids:
                err_message = _('Please select Labors to assign!')
        return err_message

    def action_assign_labor(self):
        assign_labor = self.env['mrp.labor.assign']
        for record in self:
            err_message = record.check_action_assign_labor()
            if err_message is not False:
                raise UserError(err_message)

            plan_id = False
            if record.mrp_plan_id:
                plan_id = record.mrp_plan_id.id

            labor_ids = record.labor_ids
            if record.labor_type == 'with_group':
                labor_ids = record.labor_group_id.labor_ids

            for labor in labor_ids:
                assign_labor.create({
                    'plan_id': plan_id,
                    'production_id': record.id,
                    'workorder_id': record.labor_workorder_id.id,
                    'labor_id': labor.id
                })
            record.reset_labor_form()

    def action_remove_labor(self):
        assign_to_delete = self.assign_ids.filtered(lambda a: a.workorder_id.state in ('pending', 'ready', 'cancel'))
        assign_to_delete.unlink()

    @api.depends('workorder_ids', 'workorder_ids.duration_expected', 'workorder_ids.duration')
    def _compute_duration(self):
        for record in self:
            workorders = record.workorder_ids
            record.duration_expected = sum(workorders.mapped('duration_expected'))
            record.duration = sum(workorders.mapped('duration'))

    @api.depends('workorder_ids', 'workorder_ids.is_user_working')
    def _compute_is_user_working(self):
        for record in self:
            workorder_ids = record.workorder_ids
            record.is_user_working = any(workorder_ids.mapped('is_user_working'))
            record.workorder_working_count = len(workorder_ids.filtered(lambda w: w.is_user_working))

    duration_expected = fields.Float('Expected Duration', compute=_compute_duration, store=False, help="Expected duration (in minutes)")
    duration = fields.Float(compute=_compute_duration, store=False, string='Actual Duration')
    is_user_working = fields.Boolean(compute=_compute_is_user_working)
    workorder_working_count = fields.Integer(compute=_compute_is_user_working)

    can_unbuild = fields.Boolean(compute='_compute_can_unbuild')
    unbuild_count = fields.Integer(compute='_compute_unbuild_count')

    @api.depends('state', 'move_finished_ids', 'move_finished_ids.move_line_ids', 'move_finished_ids.move_line_ids.qty_done', 'move_finished_ids.move_line_ids.unbuild_qty')
    def _compute_can_unbuild(self):
        for record in self:
            can_unbuild = False
            if record.state == 'done':
                finished_moves = record.move_finished_ids.filtered(lambda o: o.finished_id and o.state == 'done')
                can_unbuild = any(move_line.unbuild_qty < move_line.qty_done for move_line in finished_moves.move_line_ids)
            record.can_unbuild = can_unbuild

    def _compute_unbuild_count(self):
        Unbuild = self.env['mrp.unbuild']
        for record in self:
            record.unbuild_count = Unbuild.search_count([('mo_id', '=', record.id)])

    def action_view_unbuilds(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp.mrp_unbuild')
        records = self.env['mrp.unbuild'].search([('mo_id', '=', self.id)])
        if not records:
            return
        if len(records) > 1:
            action['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('mrp.mrp_unbuild_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(s, v) for s, v in action['views'] if v != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = records.id
        action['context'] = str(dict(eval(action.get('context', '').strip() or '{}', self._context), create=False))
        return action


    """ 
    OPTIMIZATION
    functions bellow is not relevan anymore.
    """
    @api.depends('product_id', 'bom_id', 'company_id')
    def _compute_allowed_product_ids(self):
        self.allowed_product_ids = [(5,)]

    @api.depends('procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids')
    def _compute_mrp_production_child_count(self):
        self.mrp_production_child_count = 0

    @api.depends('move_dest_ids.group_id.mrp_production_ids')
    def _compute_mrp_production_source_count(self):
        self.mrp_production_source_count = 0

    @api.depends('procurement_group_id.mrp_production_ids')
    def _compute_mrp_production_backorder(self):
        self.mrp_production_backorder_count = 0

    @api.depends('move_raw_ids', 'state', 'date_planned_start', 'move_raw_ids.forecast_availability', 'move_raw_ids.forecast_expected_date')
    def _compute_components_availability(self):
        self.components_availability = False
        self.components_availability_state = 'available'

    @api.depends('product_id.tracking')
    def _compute_show_lots(self):
        self.show_final_lots = False

    @api.depends('move_finished_ids.move_line_ids')
    def _compute_lines(self):
        self.finished_move_line_ids = [(5,)]

    @api.depends('workorder_ids.state')
    def _compute_workorder_done_count(self):
        self.workorder_done_count = 0

    def _compute_scrap_move_count(self):
        self.scrap_count = 0

    @api.onchange('qty_producing', 'lot_producing_id')
    def _onchange_producing(self):
        pass

    @api.onchange('lot_producing_id')
    def _onchange_lot_producing(self):
        pass


def action_confirm(self):
    self._check_company()
    for production in self:
        if production.bom_id:
            production.consumption = production.bom_id.consumption
        if not production.move_raw_ids:
            raise UserError(_("Add some materials to consume before marking this MO as to do."))
        # In case of Serial number tracking, force the UoM to the UoM of product
        if production.product_tracking == 'serial' and production.product_uom_id != production.product_id.uom_id:
            production.write({
                'product_qty': production.product_uom_id._compute_quantity(production.product_qty, production.product_id.uom_id),
                'product_uom_id': production.product_id.uom_id
            })
            for move_finish in production.move_finished_ids.filtered(lambda m: not m.byproduct_id):
                move_finish.write({
                    'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty, move_finish.product_id.uom_id),
                    'product_uom': move_finish.product_id.uom_id
                })
        production.move_raw_ids._adjust_procure_method()
        (production.move_raw_ids | production.move_finished_ids)._action_confirm()
        production.workorder_ids._action_confirm()
        # run scheduler for moves forecasted to not have enough in stock
        production.move_raw_ids._trigger_scheduler()
    return True


def _create_workorder(self):
    for production in self:
        if not production.bom_id:
            continue
        workorders_values = []

        product_qty = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
        exploded_boms, dummy = production.bom_id.explode(production.product_id, product_qty / production.bom_id.product_qty, picking_type=production.bom_id.picking_type_id)

        for bom, bom_data in exploded_boms:
            # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
            if not (bom.operation_ids and (not bom_data['parent_line'] or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                continue
            
            tool_ids = bom.tool_ids if self.env.company.bom_tools else self.env['mrp.bom.tools']
            for operation in bom.operation_ids:
                workcenter_id = operation._get_workcenter()
                values = {
                    'name': operation.name,
                    'production_id': production.id,
                    'workcenter_id': workcenter_id.id,
                    'location_id': workcenter_id.location_id.id,
                    'product_uom_id': production.product_uom_id.id,
                    'operation_id': operation.id,
                    'state': 'pending',
                    'consumption': production.consumption,
                    'tool_ids': [(6, 0, tool_ids.filtered(lambda t: t.operation_id == operation).ids)]
                }
                workorders_values += [values]

        production.workorder_ids = [(5, 0)] + [(0, 0, value) for value in workorders_values]
        for workorder in production.workorder_ids:
            workorder.duration_expected = workorder._get_duration_expected()


def _get_moves_finished_values(self):
    moves = []
    for production in self:
        if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
            raise UserError(_("You cannot have %s  as the finished product and in the Byproducts", self.product_id.name))
        
        for finished in production.bom_id.finished_ids:
            product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
            qty = finished.product_qty * (product_uom_factor / production.bom_id.product_qty)
            finished_values = production.with_context(finished_id=finished.id)._get_move_finished_values(
                finished.product_id.id, qty, finished.product_uom_id.id)
            moves.append(finished_values)

        for byproduct in production.bom_id.byproduct_ids:
            product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
            qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
            moves.append(production._get_move_finished_values(
                byproduct.product_id.id, qty, byproduct.product_uom_id.id,
                byproduct.operation_id.id, byproduct.id))
    return moves
