from odoo import models, fields, api, _
from datetime import datetime,date,timedelta
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools import float_compare

class MaintenanceRepairOrder(models.Model):
    _name = 'maintenance.repair.order'
    _inherit = ['maintenance.facilities.area','mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Repair Order'

    @api.depends('maintenance_materials_list_ids.price_total')
    def _amount_all_material(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.maintenance_materials_list_ids:
                if line.types == 'add':
                    line._compute_amount_price()
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
                else:
                    line._compute_amount_price()
                    amount_untaxed += 0
                    amount_tax += 0
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    name = fields.Char(string='Repair Order', default='New', copy=False)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    created_date = fields.Date(string='Create Date', default=datetime.today().date(), readonly=True)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    partner_id = fields.Many2one('res.partner', string='Customer')
    facilities_area = fields.Many2one(comodel_name='maintenance.facilities.area', string='Facilities Area')
    maintenance_team = fields.Many2one(comodel_name='maintenance.teams', string='Maintenance Team', ondelete='restrict')
    maintenance_assignation_type = fields.Many2one(comodel_name='maintenance.assignation.type', string='Maintenance Assignation Type')
    approvalmatrix = fields.Many2one('approval.matrix.mro', string='Approval Matrix', required=False, readonly=True, compute='_compute_approvalmatrix_mro')
    is_waiting_for_other_approvers = fields.Boolean(string='Waiting other approvers')
    approvers_id = fields.Many2many('res.users', string='Approvers')
    date_start = fields.Date(string='Start Date', required=True, default=datetime.today())
    date_stop = fields.Date(string='End Date', required=True, default=datetime.today())
    ref = fields.Char('Refrence Document', readonly=True)
    equipment_ids = fields.One2many('maintenance.equipment', 'repair_order_id')
    instruction = fields.Html(string='Instruction')
    remarks = fields.Text('Remarks')
    analytic_group_id = fields.Many2many('account.analytic.tag', string='Analytic Group')
    work_order_id = fields.Many2one('maintenance.work.order', string='Work Order')
    task_check_list_ids = fields.One2many('plan.task.check.list','maintenance_ro_id',string='Task Checklist')
    maintenance_materials_list_ids = fields.One2many('maintenance.materials.list','maintenance_ro_id', string='Materials')
    tools_materials_list_ids = fields.One2many('tools.materials.list', 'maintenance_ro_id', string='Tools Materials')
    vehicle_parts_ids = fields.Many2many(comodel_name='vehicle.parts', string='Parts')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    state_id = fields.Selection(
        [('draft', 'Draft'), ('in_progress', 'In Progress'),
         ('pending', 'Pause'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],string="State", default='draft', group_expand='_expand_states', copy=False)
    time_ids = fields.One2many(
        'time.progress', 'repair_id', copy=False)
    time_in_progress = fields.Float('Time in progress', compute='_compute_duration', inverse='_set_duration',
        readonly=False, store=True, copy=False)
    time_post_ids = fields.One2many(
        'time.post', 'repair_id', copy=False)
    time_post = fields.Float('Time Pause', compute='_compute_post_duration', inverse='_set_post_duration',
        readonly=False, store=True, copy=False)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all_material', tracking=True)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all_material')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all_material')

    maintenance_types = fields.Many2many('maintenance.type', string='Maintenance Types')
    material_request_count = fields.Integer(string='Material Request', compute='_compute_material_request_count')

    # < field for kanban view
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    color = fields.Integer('Color Index', compute='_compute_is_expired')
    # />
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly= True)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Invoice Status', readonly=True, related='invoice_id.state')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='# of Invoices')

    delivery_order_count = fields.Integer(compute='_compute_delivery_order_count', string='# of Delivery Orders')
    receiving_notes_count = fields.Integer(compute='_compute_receiving_notes_count', string='Count of Receiving Notes')

    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', compute='_compute_isapprovalmatrix')
    is_material_not_available = fields.Boolean('Material Not Available', default=False)
    is_expired_draft = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    is_expired_progress = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    replacement_parts_line = fields.One2many(comodel_name='replacement.parts.line', inverse_name='maintenance_ro_id', string='Replacement Parts')
    
    @api.model
    def default_get(self, field_list):
        res = super(MaintenanceRepairOrder, self).default_get(field_list)
        context = self._context or {}
        if context.get('active_model') == 'maintenance.equipment':
            maintenance_equipment = self.env['maintenance.equipment'].browse(context.get('active_id'))
            if res.get('department_ids'):
                res['department_ids'] = [(4, maintenance_equipment.department_id.id)]
            res['branch_id'] = maintenance_equipment.branch_id.id
            equipment = [(0, 0, {
                                'equipment_id': maintenance_equipment.id,
                            })]
            res['task_check_list_ids'] = equipment
        return res

    @api.depends('branch_id')
    def _compute_isapprovalmatrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mro')])
        approval =  IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mro')
        for record in self:
            if is_there:
                record.is_approval_matrix = approval
            else:
                record.is_approval_matrix = False

    def _compute_delivery_order_count(self):
        for order in self:
            order.delivery_order_count = self.env['stock.picking'].search_count([('mro_id', '=', order.id)])

    def _compute_receiving_notes_count(self):
        for order in self:
            order.receiving_notes_count = self.env['stock.picking'].search_count([('repair_order_id', '=', order.id)])

    def action_delivery_order(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('mro_id', '=', self.id)]
        return action

    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = self.env['account.move'].search_count([('id', '=', order.invoice_id.id)])

    def _compute_material_request_count(self):
        for order in self:
            mr = self.env['material.request'].search_count([('maintenance_ro_id', '=', order.id)])
            if mr:
                order.material_request_count = mr
            else:
                order.material_request_count = 0

    def action_view_material_request(self):
        action = self.env.ref('equip3_inventory_operation.material_request_action').read()[0]
        action['domain'] = [('maintenance_ro_id', '=', self.id)]
        return action

    @api.model
    def _expand_states(self, states, domain, order=None):
        return ['draft', 'in_progress', 'pending', 'done', 'cancel']

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        # Need a loss in case of the real time exceeding the expected
        return {
            'repair_id': self.id,
            'date_start': date_start,
            'date_end': date_end,
        }

    @api.depends('time_ids.duration', 'state_id')
    def _compute_duration(self):
        for order in self:
            order.time_in_progress = sum(order.time_ids.mapped('duration'))

    def _set_duration(self):

        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duation = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.time_in_progress
            if new_order_duration == old_order_duation:
                continue

            delta_duration = new_order_duration - old_order_duation

            if delta_duration > 0:
                date_start = datetime.now() - timedelta(seconds=_float_duration_to_second(delta_duration))
                self.env['time.progress'].create(
                    order._prepare_timeline_vals(delta_duration, date_start, datetime.now())
                )
            else:
                duration_to_remove = abs(delta_duration)
                timelines = order.time_ids.sorted(lambda t: t.date_start)
                timelines_to_unlink = self.env['time.progress']
                for timeline in timelines:
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(seconds=_float_duration_to_second(new_time_line_duration))
                        break
                timelines_to_unlink.unlink()

    @api.depends('time_post_ids.duration', 'state_id')
    def _compute_post_duration(self):
        for order in self:
            order.time_post = sum(order.time_post_ids.mapped('duration'))

    def _set_post_duration(self):

        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duation = sum(order.time_post_ids.mapped('duration'))
            new_order_duration = order.time_post
            if new_order_duration == old_order_duation:
                continue

            delta_duration = new_order_duration - old_order_duation

            if delta_duration > 0:
                date_start = datetime.now() - timedelta(seconds=_float_duration_to_second(delta_duration))
                self.env['time.post'].create(
                    order._prepare_timeline_vals(delta_duration, date_start, datetime.now())
                )
            else:
                duration_to_remove = abs(delta_duration)
                timelines = order.time_post_ids.sorted(lambda t: t.date_start)
                timelines_to_unlink = self.env['time.post']
                for timeline in timelines:
                    if duration_to_remove <= 0.0:
                        break
                    if timeline.duration <= duration_to_remove:
                        duration_to_remove -= timeline.duration
                        timelines_to_unlink |= timeline
                    else:
                        new_time_line_duration = timeline.duration - duration_to_remove
                        timeline.date_start = timeline.date_end - timedelta(seconds=_float_duration_to_second(new_time_line_duration))
                        break
                timelines_to_unlink.unlink()

    @api.depends('maintenance_materials_list_ids.price_subtotal')
    def _amount_all(self):
        for record in self:
            record.amount_total = sum(record.maintenance_materials_list_ids.mapped('price_subtotal'))

    def check_equipment_state(self):
        for order in self:
            for line in order.task_check_list_ids:
                if line.equipment_id and line.equipment_id.state == 'maintenance':
                    raise UserError(_('The asset and/or vehicle that you want to maintain is still under maintenance from other Maintenance Work Order and/or Maintenance Repair Order. Please finish that particular order first.'))

    def update_equipment_state(self):
        plan_obj = self.env['plan.task.check.list']
        for order in self:
            for line in order.task_check_list_ids:
                if line.equipment_id:
                    if order.state_id == 'in_progress':
                        line.equipment_id.write({'state': 'maintenance'})
                    # elif order.state_id == 'pending':
                    #     line.equipment_id.write({'state': 'breakdown'})
                    elif order.state_id == 'done':
                        lines = plan_obj.search([('equipment_id', '=', line.equipment_id.id), ('maintenance_ro_id.state_id', 'in', ('in_progress', 'pending'))])
                        if not lines:
                            line.equipment_id.write({'state': 'operative'})
                    elif order.state_id == 'cancel':
                        lines = plan_obj.search([('equipment_id', '=', line.equipment_id.id), ('maintenance_wo_id.state_id', 'in', ('in_progress', 'pending'))])
                        if not lines:
                            line.equipment_id.write({'state': 'operative'})

    def is_approval_matrix_defined(self):
        is_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_approval_matix_mro')
        if is_approval_matrix == 'True':
            return True
        else:
            return False

    def state_confirm(self):
        materials = self.maintenance_materials_list_ids
        location_id = []
        is_available = True
        for material in materials:
            if material.types == 'add' and material.product_id.type == 'product':
                material_stock = self.env['stock.quant'].search([('product_id', '=', material.product_id.id), ('location_id', '=', material.location_id.id), ('company_id', '=', self.env.company.id)])
                for material_stock in material_stock:
                    if material_stock.available_quantity < material.product_uom_qty:
                        is_available = False
                        self.is_material_not_available = True
        if not is_available:
            wizard = self.env['warning.wizard'].create({})
            return wizard.show_message("The materials you requested are not enough. You can filled in a Materials Request for an extra quantity.")
        else:
            self.is_material_not_available = False
            for material in materials:
                if material.types == 'add' and material.product_id.type in ['product', 'consu']:
                    if location_id == []:
                        loc_vals = {'location_id': material.location_id.id, 'location_dest_id': material.location_dest_id.id}
                        location_id.append(loc_vals)
                    else:
                        for loc in location_id:
                            if loc['location_id'] == material.location_id.id and loc['location_dest_id'] == material.location_dest_id.id:
                                break
                            else:
                                loc_vals = {'location_id': material.location_id.id, 'location_dest_id': material.location_dest_id.id}
                                location_id.append(loc_vals)

        unique_location = [i for n, i in enumerate(location_id) if i not in location_id[n + 1:]]
        for loc in unique_location:
        # for loc in location_id:
            material_ids = []
            for material in materials:
                if material.types == 'add' and material.product_id.type in ['product', 'consu']:
                    if loc['location_id'] == material.location_id.id and loc['location_dest_id'] == material.location_dest_id.id:
                        material_ids.append(material.id)
            stock_picking = self.env['stock.picking'].create({
                'mro_id': self.id,
                # 'picking_type_id': self.env.ref('stock.picking_type_out').id,
                'picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'outgoing'),('default_location_src_id', '=', loc['location_id'])], limit=1).id,
                'location_id': loc['location_id'],
                'location_dest_id': loc['location_dest_id'],
                'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                'origin': self.name,
                'company_id': self.company_id.id,
                'branch_id': self.branch_id.id,
                'scheduled_date': fields.Datetime.now(),
            })
            for material in material_ids:
                self.env['stock.move'].create({
                    'picking_id': stock_picking.id,
                    'name': materials.browse(material).product_id.name,
                    'product_id': materials.browse(material).product_id.id,
                    'product_uom_qty': materials.browse(material).product_uom_qty,
                    'product_uom': materials.browse(material).uom_id.id,
                    'location_id': materials.browse(material).location_id.id,
                    'location_dest_id': materials.browse(material).location_dest_id.id,
                    'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                    'date': fields.Datetime.now(),
                    # 'quantity_done': materials.browse(material).product_uom_qty,
                })

            stock_picking.action_assign()
        # ------ create receiving notes ------
        remove_type_material = materials.filtered(lambda l:l.types == 'remove')
        destination_location = remove_type_material.mapped('location_dest_id.id')
        if len(destination_location):
            source_location = self.env['stock.location'].search([('name','ilike','Scrap'), ('company_id','=', self.env.company.id)], limit=1)
            for i in destination_location:
                ba_material_list = []
                for m in materials:
                    if m.location_dest_id.id == i:
                        ba_material_list.append(m)
                if len(ba_material_list):
                    receiving_notes = self.env['stock.picking'].create({
                        'repair_order_id': self.id,
                        'location_id': source_location.id,
                        'location_dest_id': i,
                        'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                        'picking_type_id': self.env['stock.picking.type'].search(
                            [('default_location_dest_id', '=', i)],
                            limit=1).id,
                        'origin': self.name,
                        'create_date': fields.Datetime.now(),
                        'create_uid': self.create_uid.id if self.create_uid else '',
                        'company_id': self.company_id.id,
                        'branch_id': self.branch_id.id,
                        'scheduled_date': fields.Datetime.now(),
                        # 'state': 'assigned',
                    })
                    # ------ create Name for receiving notes ------
                    current_date = date.today()
                    date_in_string = current_date.strftime('%d/%m/%Y')
                    if receiving_notes:
                        # name = 'RCN'+'/'+date_in_string+'/' + str(receiving_notes.id)
                        # receiving_notes.name = name
                        for rec in ba_material_list:
                            # receiving_notes.receiving_notes_material_line_ids = [(0, 0, {
                            receiving_notes.move_ids_without_package = [(0, 0, {
                                'product_id': rec.product_id.id,
                                'name': rec.product_id.name,
                                'picking_id': receiving_notes.id,
                                'picking_type_id': self.env['stock.picking.type'].search(
                                        [('default_location_dest_id', '=', i)],
                                        limit=1).id,
                                'product_uom_qty': rec.product_uom_qty,
                                'product_uom':rec.uom_id.id,
                                'location_id': rec.location_id.id,
                                'location_dest_id': rec.location_dest_id.id,
                                'date': fields.Datetime.now(),
                                'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                                # 'quantity_done': rec.product_uom_qty,
                            })]

        # self.check_equipment_state()
        previous_state = self.state_id
        self.write({'state_id': 'in_progress'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)
        self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )

        self.update_equipment_state()

    def create_material_request(self):
        location_ids = []
        for line in self.maintenance_materials_list_ids:
            location_ids.append(line.location_id.id)

        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id),
                                                           ('lot_stock_id', 'in', location_ids)],limit=1)
        view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
        product_line = []
        for record in self.maintenance_materials_list_ids:
            vals = {}
            vals['product'] = record.product_id.id
            vals['quantity'] = record.product_uom_qty
            vals['product_unit_measure'] = record.uom_id.id
            vals['destination_warehouse_id'] = warehouse_id.id
            product_line.append([0, 0, vals])
        ctx = {
            'default_company_id': self.company_id.id,
            'default_branch_id': self.branch_id.id,
            'default_schedule_date': fields.date.today(),
            'default_product_line': product_line,
            'default_destination_warehouse_id': warehouse_id.id,
            'default_maintenance_ro_id': self.id,
        }
        return {
            'name': 'Create Material Request',
            'type': 'ir.actions.act_window',
            'res_model': 'material.request',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': ctx,
        }

    def state_pending(self):
        previous_state = self.state_id
        self.write({'state_id': 'pending'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)
        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        self.env['time.post'].create(
            self._prepare_timeline_vals(self.time_post, datetime.now())
        )

        self.update_equipment_state()

    def action_start_again(self):
        # self.check_equipment_state()
        previous_state = self.state_id

        self.write({'state_id': 'in_progress'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)
        self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()

    def state_cancel(self):
        previous_state = self.state_id
        self.write({'state_id': 'cancel'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)
        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'maintenance.repair.order.sequence') or 'New'
        vals.update({'branch': vals.get('branch_id', self.env.user.branch_id.id)})
        self.get_value_materials()
        self.get_tools_list()
        return super(MaintenanceRepairOrder, self).create(vals)
    def write(self, vals):
        res = super(MaintenanceRepairOrder, self).write(vals)
        self.get_value_materials()
        self.get_tools_list()
        self.get_current_parts()
        return res

    def replacement_parts(self):
        for line in self.replacement_parts_line.filtered(lambda r: r.replacement_part_id):
            for vehicle in line.asset_vehicle_id.vehicle_parts_ids:
                if vehicle.equipment_id.id == line.current_part_id.id:
                    vehicle.write({
                        'equipment_id': line.replacement_part_id.id,
                        'serial_no': line.new_part_serial,
                    })

    def replacement_parts_history(self):
        for line in self.replacement_parts_line.filtered(lambda r: r.replacement_part_id):
            self.env['parts.replacement.history.line'].create({
                'equipment_id': line.asset_vehicle_id.id,
                'maintenance_ro_id': self.id,
                'old_part_id': line.current_part_id.id,
                'old_part_sn': line.current_serial_number,
                'new_part_id': line.replacement_part_id.id,
                'new_part_sn': line.new_part_serial,
                'replace_date': datetime.now(),
            })
            
    def state_done(self):
        self._check_asset_budget_amount()
        self.replacement_parts()
        self.write({'state_id': 'done'})
        self.replacement_parts_history()
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()

        self.update_equipment_state()

        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        stock_pickings = self.env['stock.picking'].search([('mro_id', 'in', self.ids)])
        for stock_picking in stock_pickings:
            if stock_picking.state != 'done':
                stock_picking.button_validate()
        # precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # Move = self.env['stock.move']
        # move = self.env['stock.move']
        # for repair in self:
        #     # delivery_order = self.env['stock.picking'].create({
        #     #     'location_id': repair.location_id.id,
        #     #     'location_dest_id': repair.location_dest_id.id,
        #     #     'company_id': repair.company_id.id,
        #     #     'scheduled_date': fields.Datetime.now(),
        #     #     'origin': repair.name,
        #     #     'repair_id': repair.id,
        #     #     'state': 'draft',
        #     # })
        #     # for material in repair.maintenance_materials_list_ids:
        #     #     if material.types == 'add' and material.product_id.type == 'product':
        #     #         Move.create({
        #     #             'name': repair.name,
        #     #             'product_id': material.product_id.id,
        #     #             'product_uom_qty': material.product_uom_qty,
        #     #             'product_uom': material.product_uom.id,
        #     #             'location_id': repair.location_id.id,
        #     #             'location_dest_id': repair.location_dest_id.id,
        #     #             'repair_id': repair.id,
        #     #             'origin': repair.name,
        #     #             'state': 'draft',
        #     #             'picking_type_id': repair.picking_type_id.id,
        #     #             'move_dest_id': delivery_order.move_lines.ids[0].id,
        #     #             'move_orig_ids': [(6, 0, [material.id])],
        #     #             'picking_id': delivery_order.id,
        #     #             'procure_method': 'make_to_stock',
        #     #             'restrict_partner_id': repair.partner_id.id,
        #     #         })
        #     ################################################################################################
        #     moves = self.env['stock.move']
        #     for operation in repair.maintenance_materials_list_ids:
        #         if operation.types == "add":
        #             if operation.product_id.type not in ['product', 'consu']:
        #                 continue
        #             move = Move.create({
        #                 'name': repair.name,
        #                 'product_id': operation.product_id.id,
        #                 'product_uom_qty': operation.product_uom_qty,
        #                 'product_uom': operation.uom_id.id,
        #                 'partner_id': repair.partner_id.id,
        #                 'location_id': operation.location_id.id,
        #                 'location_dest_id': operation.location_dest_id.id,
        #                 'origin': repair.name,
        #                 'company_id': repair.company_id.id,
        #             })

        #             # Best effort to reserve the product in a (sub)-location where it is available
        #             product_qty = move.product_uom._compute_quantity(
        #                 operation.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')
        #             available_quantity = self.env['stock.quant']._get_available_quantity(
        #                 move.product_id,
        #                 move.location_id,
        #                 strict=False,
        #             )
        #             move._update_reserved_quantity(
        #                 product_qty,
        #                 available_quantity,
        #                 move.location_id,
        #                 strict=False,
        #             )
        #             # Then, set the quantity done. If the required quantity was not reserved, negative
        #             # quant is created in operation.location_id.
        #             move._set_quantity_done(operation.product_uom_qty)

        #             moves |= move
        #             operation.write({'move_id': move.id})
        #     if moves:
        #         consumed_lines = moves.mapped('move_line_ids')
        #         produced_lines = move.move_line_ids
        #         moves |= move
        #         moves._action_done()
        #         produced_lines.write({'consume_line_ids': [(6, 0, consumed_lines.ids)]})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Maintenance Repair Order '),
            'template': '/equip3_asset_fms_operation/static/xls/repair_order_template.xls'
        }]

    def get_value_materials(self):
            for record in self:
                equipment_ids = record.task_check_list_ids.filtered(lambda r: not r.already_compute).mapped('equipment_id')
                materials = record.env['maintenance.equipment.materials.list'].read_group(
                    domain=[('equipment_id', 'in', equipment_ids.ids)],
                    fields=['uom_id', 'product_id', 'product_uom_qty', 'location_id', 'location_dest_id', 'equipment_id', 'equipment_part_id', 'price_unit'],
                    groupby=['uom_id', 'product_id', 'location_id', 'location_dest_id', 'equipment_id', 'equipment_part_id', 'price_unit'],
                    lazy=False)

                existing_materials = record.maintenance_materials_list_ids.mapped('parent_equipment_id')

                materials_to_create = []
                for material in materials:
                    product_id = self.env['product.product'].browse(material.get('product_id')[0])
                    parent_equipment_id = self.env['maintenance.equipment'].browse(material.get('equipment_id')[0])
                    if parent_equipment_id not in existing_materials:
                        location_id = self.env['stock.location'].browse(material.get('location_id')[0])
                        location_dest_id = self.env['stock.location'].browse(material.get('location_dest_id')[0])
                        material_data = {
                            'product_id': product_id.id,
                            'parent_equipment_id': material.get('equipment_id')[0],
                            'part_equipment_id': material.get('equipment_part_id')[0] if material.get('equipment_part_id') else False,
                            'product_uom_qty': material.get('product_uom_qty'),
                            'uom_id': material.get('uom_id')[0],
                            'location_id': location_id.id,
                            'location_dest_id': location_dest_id.id,
                            'price_unit': material.get('price_unit'),
                        }
                        materials_to_create.append((0, 0, material_data))

                try:
                    if materials_to_create:
                        # print("➡ materials_to_create :", materials_to_create)
                        record.write({'maintenance_materials_list_ids': materials_to_create})
                    record.task_check_list_ids.write({'already_compute': True})
                except Exception as e:
                    pass

    def get_tools_list(self):
        for record in self:
            if record.task_check_list_ids.equipment_id.tools_materials_list_ids:
                for line in record.task_check_list_ids.equipment_id.tools_materials_list_ids:
                    if line.product_id not in record.tools_materials_list_ids.mapped('product_id'):
                        record.tools_materials_list_ids = [(0, 0,{
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_uom_qty,
                            'uom_id': line.uom_id.id
                        })]

    def get_current_parts(self):
        if not self._context.get('replace_part'):
            equiment_from_vehicle_parts = [vehicle_part for line in self.task_check_list_ids for vehicle_part in line.equipment_id.vehicle_parts_ids.ids]
            vehicle_parts = self.env['vehicle.parts'].search([('id','in',equiment_from_vehicle_parts)])
            for record in self:
                for vehicle in vehicle_parts:
                    if vehicle.equipment_id.id not in record.replacement_parts_line.mapped('current_part_id').ids:
                        record.replacement_parts_line = [(0, 0,{
                            'maintenance_ro_id': record.id,
                            'asset_vehicle_id': vehicle.maintenance_equipment_id.id,
                            'current_part_id': vehicle.equipment_id.id,
                            'current_serial_number': vehicle.equipment_id.serial_no,
                        })]
            for line in record.replacement_parts_line:
                if line.current_part_id.id not in vehicle_parts.mapped('equipment_id').ids:
                    line.unlink()

    def create_ro_invoice(self):
        # raise Warning(_('Please create invoice for this work order'))
        ro_id = self.id
        vals_line = []
        for line in self.maintenance_materials_list_ids:
            if line.product_id.property_account_income_id:
                income_account = line.product_id.property_account_income_id.id
            elif line.product_id.categ_id.property_account_income_categ_id:
                income_account = line.product_id.categ_id.property_account_income_categ_id.id
            else:
                raise UserError(_('Please define income '
                                'account for this product: "%s" (id:%d).')
                                % (line.product_id.name, line.product_id.id))
            if line.types == 'add':
                vals_line.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.invoiced_price,
                    'name': self.name,
                    'account_id': income_account,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                    'price_subtotal': line.price_subtotal,
                }))
        vals = {
            'repair_order_id': ro_id,
            'move_type': 'out_invoice',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'invoice_date_due': self.date_stop,
            'invoice_date': self.date_start,
            'invoice_user_id': self.user_id.id,
            'invoice_line_ids': vals_line,
        }
        invoice = self.env['account.move'].create(vals)
        if invoice:
            self.invoice_id = invoice.id

    def button_cancel(self):
        for record in self:
            record.invoice_id.action_cancel()
            record.invoice_id = False

    def action_view_invoice(self):
        invoices = self.env['account.move'].search([('id','=',self.invoice_id.id)])
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_receiving_notes(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('repair_order_id', '=', self.id)]
        return action

    @api.depends('branch_id', 'amount_total')
    def _compute_approvalmatrix_mro(self):
        self.approvalmatrix = self.env['approval.matrix.mro'].search([('branch_id', '=', self.branch_id.id), ('min_amount', '<=', self.amount_total), ('max_amount', '>=', self.amount_total)], limit=1)

    def _is_unauthorized_user(self):
        if self.env.user not in self.approvalmatrix.approval_matrix_mro_ids.mapped('user_id'):
            raise ValidationError('You are not allowed to do this action')

    # fungsi untuk cek apakah sudah mecapai minimum approvers
    def _is_enough_approvers(self, previous_state):
        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()
        line = self.approvalmatrix.approval_matrix_mro_ids
        if len(self.approvers_id) < line.min_approvers: # belum cukup
            for user in line.mapped('user_id'):
                if user in self.approvers_id:
                    continue
                self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
                self.state_id = previous_state
        else:
            self.approvers_id = [(5)]

    def _compute_is_expired(self):
        today = fields.Date.context_today(self)

        expired_draft_orders = self.filtered(lambda order: order.state_id == 'draft' and order.date_start < today)
        expired_progress_orders = self.filtered(lambda order: order.state_id in ['in_progress', 'pending'] and order.date_stop < today)

        expired_draft_orders.update({
            'is_expired_draft': True,
            'color': 1,
        })

        expired_progress_orders.update({
            'is_expired_progress': True,
            'color': 2,
        })

        remaining_orders = self - expired_draft_orders - expired_progress_orders

        remaining_orders.update({
            'is_expired_draft': False,
            'is_expired_progress': False,
            'color': False,
        })

        # Update is_expired_draft for non-expired orders
        non_expired_orders_draft = self - expired_draft_orders
        non_expired_orders_draft.update({
            'is_expired_draft': False,
        })
        # Update is_expired_progress for non-expired orders
        non_expired_orders_progress = self - expired_progress_orders
        non_expired_orders_progress.update({
            'is_expired_progress': False,
        })
        
    def get_selection_label(self, field_name, field_value):
        field = self._fields.get(field_name)
        if field and field.type == 'selection':
            selection_dict = dict(self._fields[field_name].selection)
            label = selection_dict.get(field_value)
        return label

    def unlink(self):
        for record in self:
            if record.state_id in ('in_progress', 'pending', 'done'):
                state_label = record.get_selection_label('state_id', record.state_id)
                if state_label:
                    raise ValidationError(f"You can not delete maintenance repair order in '{state_label}' status")
        return super(MaintenanceRepairOrder, self).unlink()

# ----- Object for 'receiving Notes' --------

class ReceivingNotesMaterialLines(models.Model):
    _name = "receiving.notes.material.lines"
    _description = 'Receiving Notes Material Lines'

    stock_picking_id = fields.Many2one('stock.picking', 'Stock Picking', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', string='Tools')
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location",
                                       domain="[('usage', '=', 'internal')]")
    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    notes = fields.Char('Notes')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    invoiced_price = fields.Float('Invoiced Price')
    taxes_id = fields.Many2many('account.tax', string='Taxes',
                                default=lambda self: self.env.company.account_sale_tax_id)
    # price_subtotal = fields.Monetary(compute='_compute_amount_price', string='Subtotal', store=True)
    price_subtotal = fields.Monetary(string='Subtotal', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    # types = fields.Selection([("add", "Add"), ("remove", "Remove")], string='Type', default="add")

    def init(self):
        delete_field_query = _("DELETE from ir_model_fields WHERE model='receiving.notes'")
        self._cr.execute(delete_field_query)

        delete_model_query = _("DELETE from ir_model WHERE model='receiving.notes'")
        self._cr.execute(delete_model_query)


class MaintenanceEquipmentExtend(models.Model):
    _inherit = "maintenance.equipment"


    repair_order_id = fields.Many2one('maintenance.repair.order', string='Maintenance Repair Order')
    workorder_ids = fields.Many2many('maintenance.work.order', string='Workorder', compute="_get_workorder")
    workorder_count = fields.Integer(string='Workorder', compute='_get_workorder')
    repair_count = fields.Integer(compute='_get_workorder')
    parts_replacement_history_line = fields.One2many(comodel_name='parts.replacement.history.line', inverse_name='equipment_id', string='Part Replacement History Line')

    def _get_workorder(self):
        self.workorder_ids = None
        self.workorder_count = None
        self.repair_count = None
        branch_ids = self.env.user.branch_ids.ids
        if len(branch_ids) == 1:
            branch_ids.append(0)
        for wo in self:
            workorders = self.env['plan.task.check.list'].search([('equipment_id', '=', wo.id)])
            if workorders:
                mwo = self.env['maintenance.work.order'].search([('id', 'in', workorders.maintenance_wo_id.ids), ('branch_id', 'in', branch_ids)])
                wo.workorder_ids = mwo.ids
                wo.workorder_count = len(mwo.ids)
            repairorders = self.env['maintenance.repair.order'].search([('id', 'in', workorders.maintenance_ro_id.ids), ('branch_id', 'in', branch_ids)])
            if repairorders:
                wo.repair_count = len(repairorders.ids)

    def action_view_workorder_ids(self):
        self.ensure_one()
        view_form_id = self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_form').id
        view_tree_id = self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.workorder_ids.ids)],
            'view_mode': 'tree,form',
            'name': _('Workorder'),
            'res_model': 'maintenance.work.order',
        }
        action['views'] = [(view_tree_id, 'tree'), (view_form_id, 'form')]
        return action

    def repair_action_link(self):
        res = super(MaintenanceEquipmentExtend, self).repair_action_link()
        repairorders = []
        branch_ids = self.env.user.branch_ids.ids
        if len(branch_ids) == 1:
            branch_ids.append(0)
        for wo in self:
            plan_task = self.env['plan.task.check.list'].search([('equipment_id', '=', wo.id)])
            repairorders = self.env['maintenance.repair.order'].search([('id', 'in', plan_task.maintenance_ro_id.ids), ('branch_id', 'in', branch_ids)])
            if repairorders:
                res['domain'] = [('id', 'in', repairorders.ids)]
            else:
                res['domain'] =  [('id', 'in', 0)]
        return res

class Repair(models.Model):
    _inherit = 'repair.order'

    def action_repair_done(self):
        if self.filtered(lambda repair: not repair.repaired):
            raise UserError(_("Repair must be repaired in order to make the product moves."))
        self._check_company()
        self.operations._check_company()
        self.fees_lines._check_company()
        res = {}
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        Move = self.env['stock.move']
        for repair in self:
            owner_id = False
            available_qty_owner = self.env['stock.quant']._get_available_quantity(repair.product_id, repair.location_id, repair.lot_id, owner_id=repair.partner_id, strict=True)
            if float_compare(available_qty_owner, repair.product_qty, precision_digits=precision) >= 0:
                owner_id = repair.partner_id.id

            moves = self.env['stock.move']
            for operation in repair.operations:
                if operation.type == 'add':
                    move = Move.create({
                        'name': repair.name,
                        'product_id': operation.product_id.id,
                        'product_uom_qty': operation.product_uom_qty,
                        'product_uom': operation.product_uom.id,
                        'partner_id': repair.address_id.id,
                        'location_id': operation.location_id.id,
                        'location_dest_id': operation.location_dest_id.id,
                        'repair_id': repair.id,
                        'origin': repair.name,
                        'company_id': repair.company_id.id,
                    })
                    product_qty = move.product_uom._compute_quantity(
                        operation.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')
                    available_quantity = self.env['stock.quant']._get_available_quantity(
                        move.product_id,
                        move.location_id,
                        lot_id=operation.lot_id,
                        strict=False,
                    )
                    move._update_reserved_quantity(
                        product_qty,
                        available_quantity,
                        move.location_id,
                        lot_id=operation.lot_id,
                        strict=False,
                    )
                    move._set_quantity_done(operation.product_uom_qty)

                    if operation.lot_id:
                        move.move_line_ids.lot_id = operation.lot_id

                    moves |= move
                    operation.write({'move_id': move.id, 'state': 'done'})
            if moves:
                move = Move.create({
                    'name': repair.name,
                    'product_id': repair.product_id.id,
                    'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
                    'product_uom_qty': repair.product_qty,
                    'partner_id': repair.address_id.id,
                    'location_id': repair.location_id.id,
                    'location_dest_id': repair.location_id.id,
                    'move_line_ids': [(0, 0, {'product_id': repair.product_id.id,
                                            'lot_id': repair.lot_id.id,
                                            'product_uom_qty': 0,  # bypass reservation here
                                            'product_uom_id': repair.product_uom.id or repair.product_id.uom_id.id,
                                            'qty_done': repair.product_qty,
                                            'package_id': False,
                                            'result_package_id': False,
                                            'owner_id': owner_id,
                                            'location_id': repair.location_id.id,
                                            'company_id': repair.company_id.id,
                                            'location_dest_id': repair.location_id.id,})],
                    'repair_id': repair.id,
                    'origin': repair.name,
                    'company_id': repair.company_id.id,
                })
                consumed_lines = moves.mapped('move_line_ids')
                produced_lines = move.move_line_ids
                moves |= move
                moves._action_done()
                produced_lines.write({'consume_line_ids': [(6, 0, consumed_lines.ids)]})
                res[repair.id] = move.id
        return res

class StockPickings(models.Model):
    _inherit = 'stock.picking'

    mro_id = fields.Many2one('maintenance.repair.order', string='Repair Order')
    repair_order_id = fields.Many2one('maintenance.repair.order', 'Repair Order', tracking=True, readonly='1')
    receiving_notes_material_line_ids = fields.One2many('receiving.notes.material.lines', 'stock_picking_id',
                                                        'Receiving Notes')

class ReplacementPartsLine(models.Model):
    _name = 'replacement.parts.line'
    _description = 'Replacement Parts Line'

    maintenance_ro_id = fields.Many2one(comodel_name='maintenance.repair.order', string='Maintenance RO')
    asset_vehicle_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset/Vehicle')
    current_part_id = fields.Many2one(comodel_name='maintenance.equipment', string='Current Part')
    current_serial_number = fields.Char(string='Current Serial Number')
    replacement_part_id = fields.Many2one(comodel_name='maintenance.equipment', string='Replacement Parts')
    new_part_serial = fields.Char(string='New Parts Serial Number')
    state = fields.Selection(string='Status', related='maintenance_ro_id.state_id')

    @api.onchange('current_part_id')
    def onchange_current_part_id(self):
        if self.current_part_id:
            self.current_serial_number = self.current_part_id.serial_no

    def action_replace(self):
        ctx = {
            'default_id': self.id,
            'default_parent_equipment_id': self.asset_vehicle_id.id,
            'default_equipment_id': self.replacement_part_id.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Action Replace Wizard',
            'res_model': 'action.replace.parts.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }


class PartsReplacementHistoryLineIds(models.Model):
    _name = 'parts.replacement.history.line'
    _description = 'Parts Replacement History Line'

    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    maintenance_ro_id = fields.Many2one(comodel_name='maintenance.repair.order', string='Maintenance Repair Order')
    old_part_id = fields.Many2one(comodel_name='maintenance.equipment', string='Old Part')
    old_part_sn = fields.Char(string='Serial Number')
    new_part_id = fields.Many2one(comodel_name='maintenance.equipment', string='New Part')
    new_part_sn = fields.Char(string='Serial Number')
    replace_date = fields.Date(string='Replace Date')
