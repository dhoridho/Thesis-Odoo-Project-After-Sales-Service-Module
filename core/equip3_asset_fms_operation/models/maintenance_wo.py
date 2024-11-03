from odoo import api, fields, models, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError, ValidationError

class MaintenanceWorkOrder(models.Model):
    _name = 'maintenance.work.order'
    _inherit = ['maintenance.facilities.area','mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Work Order'
    _parent_name = "parent_location"
    _rec_name = 'name'

    @api.depends('maintenance_materials_list_ids.price_total')
    def _amount_all_material(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.maintenance_materials_list_ids:
                line._compute_amount_price()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    name = fields.Char("Work Order",default='New', copy=False)
    facility = fields.Many2one(comodel_name='maintenance.facilities.area', string='Facilities Area')
    partner_id = fields.Many2one('res.partner', string='Customer')
    startdate = fields.Date(string='Start Date',default=datetime.today().date())
    enddate = fields.Date(string='End Date',default=datetime.today().date())
    branch_id = fields.Many2one('res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    maintenanceteam = fields.Many2one(comodel_name='maintenance.teams', string='Maintenance Team', ondelete='restrict')
    maintenanceassign = fields.Many2one('maintenance.assignation.type', string='Maintenance Assignation Type')
    approvalmatrix = fields.Many2one('approval.matrix.mwo', string='Approval Matrix', required=True, readonly=True)
    created_date = fields.Datetime(string='Create Date', readonly=True, default=datetime.today().date())
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", "Company",required=True, readonly=True, default=lambda self: self.env.user.company_id)
    instructions = fields.Html(string='instructions')
    work_order_line_ids = fields.One2many('maintenance.work.order.line','work_order_id', string='WO Line')
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    ref = fields.Char('Reference Document', readonly=True)
    remarks = fields.Text('Remarks')
    analytic_group_id = fields.Many2many('account.analytic.tag', string='Analytic Group')
    task_check_list_ids = fields.One2many('plan.task.check.list','maintenance_wo_id',string='Asset Checklist')
    maintenance_materials_list_ids = fields.One2many('maintenance.materials.list','maintenance_wo_id', string='Materials')
    tools_materials_list_ids = fields.One2many('tools.materials.list', 'maintenance_wo_id', string='Tools Materials')
    repair_count = fields.Integer(string='Repair Count', compute='_compute_repair_count')
    repair_ids = fields.Many2many('maintenance.repair.order', string='Repair Orders', compute="_compute_repair_count")
    attach_count = fields.Integer(string='Attachment', compute="_compute_attachment_count")
    maintenance_plan_id = fields.Many2one('maintenance.plan', string='Refrence Document', readonly=True)
    vehicle_parts_ids = fields.Many2many(comodel_name='vehicle.parts', string='Parts')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset')
    task = fields.Text('Task')
    parent_location = fields.Many2one(
        'maintenance.work.order', 'Parent Location', index=True, ondelete='cascade', check_company=True,
        help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location.")
    child_ids = fields.One2many('maintenance.work.order', 'parent_location', 'Contains')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    state_id = fields.Selection(
        [('draft', 'Draft'),
         ('to_approve', 'Waiting for Approval'),
         ('in_progress', 'In Progress'),
         ('to_approve_post', 'Waiting for Approval'),
         ('pending', 'Pause'),
         ('to_approve_done', 'Waiting for Approval'),
         ('done', 'Done'),
         ('to_approve_cancel', 'Waiting For Approval'),
         ('cancel', 'Cancelled')], string="State", default='draft', group_expand='_expand_states', copy=False)
    time_ids = fields.One2many(
        'time.progress', 'maintenance_wo_id', copy=False)
    time_in_progress = fields.Float('Time in progress', compute='_compute_duration', inverse='_set_duration',
        readonly=False, store=True, copy=False)
    time_post_ids = fields.One2many(
        'time.post', 'maintenance_wo_id', copy=False)
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
    is_material_not_available = fields.Boolean('Material Not Available',default=False)
    is_expired_draft = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    is_expired_progress = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    remaining_budget = fields.Monetary(string='Remaining Budget')
    stock_move_count = fields.Integer(compute='_compute_stock_move_count', string='# of Stock Moves')

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        self.branch = self.branch_id.id

    def _compute_stock_move_count(self):
        for rec in self:
            rec.stock_move_count = self.env['stock.move'].search_count([('mwo_id', '=', rec.id)])
                
    def action_view_stock_move(self):
        action = self.env.ref('stock.stock_move_action').read()[0]
        action['domain'] = [('mwo_id', '=', self.id)]
        action['context'] = {}
        return action
        
    def _compute_delivery_order_count(self):
        for order in self:
            order.delivery_order_count = self.env['stock.picking'].search_count([('mwo_id', '=', order.id)])
            
    def action_delivery_order(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('mwo_id', '=', self.id)]
        return action


    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = self.env['account.move'].search_count([('id', '=', order.invoice_id.id)])

    @api.model
    def _expand_states(self, states, domain, order):
        return ['draft', 'in_progress', 'pending', 'done', 'cancel']

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        # Need a loss in case of the real time exceeding the expected
        return {
            'maintenance_wo_id': self.id,
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
                        lines = plan_obj.search([('equipment_id', '=', line.equipment_id.id), ('maintenance_wo_id.state_id', 'in', ('in_progress', 'pending'))])
                        if not lines:
                            line.equipment_id.write({'state': 'operative'})
                    elif order.state_id == 'cancel':
                        lines = plan_obj.search([('equipment_id', '=', line.equipment_id.id), ('maintenance_wo_id.state_id', 'in', ('in_progress', 'pending'))])
                        if not lines:
                            line.equipment_id.write({'state': 'operative'})

    def state_confirm(self):
        # self.check_equipment_state()
        materials = self.maintenance_materials_list_ids
        for material in materials:
            if material.product_id.type == 'product':
                material_stock = self.env['stock.quant'].search([('product_id', '=', material.product_id.id), ('location_id', '=', material.location_id.id)])
                if material_stock.quantity < material.product_uom_qty:
                    raise Warning(_('The materials you requested are not enough. You can filled in a Materials Request for an extra quantity'))

        self.write({'state_id': 'in_progress'})
        self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )

        self.update_equipment_state()

    def create_material_request(self):
        location_ids = []
        for line in self.maintenance_materials_list_ids:
            location_ids.append(line.location_id.id)

        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id),
                                                        ('lot_stock_id', 'in', location_ids),],limit=1)
        product_line = []
        for record in self.maintenance_materials_list_ids:
            vals = {}
            vals['product'] = record.product_id.id
            vals['quantity'] = record.product_uom_qty
            vals['product_unit_measure'] = record.uom_id.id
            vals['destination_warehouse_id'] = warehouse_id.id
            product_line.append([0, 0, vals])
        ctx = {
            'default_destination_warehouse_id': warehouse_id.id,
            'default_company_id': self.company_id.id,
            'default_branch_id': self.branch_id.id,
            'default_schedule_date': fields.date.today(),
            'default_product_line': product_line,
            'default_maintenance_wo_id': self.id,
        }
        view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
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

    def state_done(self):
        self.write({'state_id': 'done'})
        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()

    def state_pending(self):
        self.write({'state_id': 'pending'})
        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        self.env['time.post'].create(
            self._prepare_timeline_vals(self.time_post, datetime.now())
        )

        self.update_equipment_state()

    def action_start_again(self):
        print('action start in wo')
        # self.check_equipment_state()

        self.write({'state_id': 'in_progress'})
        self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()

    def state_cancel(self):
        self.write({'state_id': 'cancel'})
        time_ids = self.time_ids.filtered(lambda r:not r.date_end)
        if time_ids:
            time_ids.write({'date_end': datetime.now()})
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()

    def _compute_repair_count(self):
        self.repair_ids = None
        self.repair_count = None
        for wo in self:
            repairs = self.env['maintenance.repair.order'].search([('work_order_id', '=', self.id)])
            if repairs:
                wo.repair_ids = repairs.ids
                wo.repair_count = len(repairs)

    def _compute_attachment_count(self):
        self.attach_count = None
        for wo in self:
            attach = self.env['ir.attachment'].search(['&', ('res_id', '=', self.id), ('res_model', '=', self._name)])
            if attach:
                # wo.repair_ids = repairs.ids
                wo.attach_count = len(attach)

    @api.depends('parent_location.name')
    def _compute_complete_name(self):
        for group in self:
            if group.parent_location:
                group.complete_name = '%s / %s' % (group.parent_location.name, group.name)
            else:
                group.complete_name = group.name

    @api.model
    def create(self, vals):
        res = super(MaintenanceWorkOrder, self).create(vals)
        if vals.get('name', _('New')) == _('New'):
            res.name = res.env['ir.sequence'].next_by_code('maintenance.work.order.sequence') or _('New')
        res.get_material_list()
        res.get_tools_list()
        return res

    def write(self, vals):
        res = super(MaintenanceWorkOrder, self).write(vals)
        self.get_material_list()
        self.get_tools_list()
        return res

    def get_material_list(self):
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

    def action_create_repair_order(self):
        repair_order_id = self.env['maintenance.repair.order'].create({
            'created_date': self.created_date,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'branch': self.branch_id.id,
            'date_start': self.startdate,
            'date_stop': self.enddate,
            'facilities_area': self.facility.id,
            'maintenance_team': self.maintenanceteam.id,
            'maintenance_assignation_type': self.maintenanceassign.id,
            'ref': self.name,
            'remarks': self.remarks,
            'analytic_group_id': self.analytic_group_id.ids,
            'work_order_id': self.id,
            'maintenance_types': [(6, 0, self.maintenance_types.ids)],
        })
        if repair_order_id:
            for tas in self.task_check_list_ids:
                repair_order_id.task_check_list_ids = [(0, 0, {
                    'equipment_id': tas.equipment_id.id,
                    'vehicle_parts_ids': [(6, 0, tas.vehicle_parts_ids.ids)],
                    'task': tas.task,
                })]
            for tools in self.tools_materials_list_ids:
                repair_order_id.tools_materials_list_ids = [(0, 0, {
                    'product_id': tools.product_id.id,
                    'uom_id': tools.uom_id.id,
                })]
            for material in self.maintenance_materials_list_ids:
                repair_order_id.maintenance_materials_list_ids = [(0, 0, {
                    'product_id': material.product_id.id,
                    'uom_id': material.uom_id.id,
                })]
                # delete material line having no location -------
                material_lines = repair_order_id.maintenance_materials_list_ids
                for i in material_lines:
                    if not i.location_id or not i.location_dest_id:
                        i.unlink()

    def repair_action_link(self):
        self.ensure_one()
        view_form_id = self.env.ref('equip3_asset_fms_operation.maintenance_repair_order_form_view').id
        view_list_id = self.env.ref('equip3_asset_fms_operation.maintenance_repair_order_tree_view').id
        action = {
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.repair_ids.ids)],
            'view_mode': 'kanban,form',
            'name': _('Repair Order'),
            'res_model': 'maintenance.repair.order',
        }
        if len(self.repair_ids) == 1:
            action.update({'views': [(view_form_id, 'form')], 'res_id': self.repair_ids.id})
        else:
            action['views'] = [(view_list_id, 'list'), (view_form_id, 'form')]
        return action

    def get_attachment(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'maintenance.work.order'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'maintenance.work.order', 'default_res_id': self.id}
        return res

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Maintenance Work Order '),
            'template': '/equip3_asset_fms_operation/static/xls/work_order_template.xls'
        }]

    def create_wo_invoice(self):
        # raise Warning(_('Please create invoice for this work order'))
        wo_id = self.id
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

            vals_line.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_id': line.uom_id.id,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'name': self.name,
                'account_id': income_account,
                'tax_ids': [(6, 0, line.taxes_id.ids)],
                'price_subtotal': line.price_subtotal,
            }))
        vals = {
            'work_order_id': wo_id,
            'move_type': 'out_invoice',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'invoice_date_due': self.enddate,
            'invoice_date': self.startdate,
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

    def _compute_material_request_count(self):
        for order in self:
            mr = self.env['material.request'].search_count([('maintenance_wo_id', '=', order.id)])
            if mr:
                order.material_request_count = mr
            else:
                order.material_request_count = 0

    def action_view_material_request(self):
        action = self.env.ref('equip3_inventory_operation.material_request_action').read()[0]
        action['domain'] = [('maintenance_wo_id', '=', self.id)]
        return action


    def _compute_is_expired(self):
        today = fields.Date.context_today(self)

        expired_draft_orders = self.filtered(lambda order: order.state_id == 'draft' and order.startdate < today)
        expired_progress_orders = self.filtered(lambda order: order.state_id in ['in_progress', 'pending'] and order.enddate < today)

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
                    raise ValidationError(f"You can not delete maintenance work order in '{state_label}' status")
        return super(MaintenanceWorkOrder, self).unlink()
        
    @api.model
    def default_get(self, field_list):
        res = super(MaintenanceWorkOrder, self).default_get(field_list)
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



class MaintenanceWorkOrderLine(models.Model):
    _name = 'maintenance.work.order.line'
    _description = 'Maintenance Work Order Line'

    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset')
    work_order_id = fields.Many2one(comodel_name='maintenance.work.order', string='Asset')

class StockPickings(models.Model):
    _inherit = 'stock.picking'

    mwo_id = fields.Many2one(comodel_name='maintenance.work.order', string='Work Order')
