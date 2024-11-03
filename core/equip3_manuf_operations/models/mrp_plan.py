import json
from odoo import fields, models, api, _, tools
from datetime import datetime, timedelta
from odoo.tools import format_datetime, float_is_zero
from odoo.exceptions import ValidationError, UserError
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from dateutil.relativedelta import relativedelta


class MrpPlan(models.Model):
    _name = 'mrp.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Plan'
    _rec_name = 'plan_id'
    _order = 'priority desc, date_planned_start asc,id'

    @api.model
    def create(self, vals):
        if vals.get('plan_id', _('New')) == _('New'):
            vals['plan_id'] = self.env['ir.sequence'].next_by_code('mrp.plan', sequence_date=None) or _('New')
        return super(MrpPlan, self).create(vals)

    def write(self, vals):
        res = super(MrpPlan, self).write(vals)
        for plan in self:
            production_ids = plan.mrp_order_ids.filtered(lambda p: not p.is_planned)
            if production_ids:
                production_ids.with_context(force_date=True).write({
                    'date_planned_start': plan.date_planned_start,
                    'date_planned_finished': plan.date_planned_finished
                })
        return res

    @api.model
    def _get_default_date_planned_finished(self):
        if self.env.context.get('default_date_planned_start'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_planned_start')) + timedelta(hours=1)
        return datetime.now() + timedelta(hours=1)

    @api.model
    def _get_default_date_planned_start(self):
        if self.env.context.get('default_date_deadline'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
        return datetime.now()

    @api.depends('mrp_order_ids', 'mrp_order_ids.reservation_state')
    def _compute_reservation_state(self):
        for plan in self:
            plan.reservation_state = 'waiting'
            if all(order.reservation_state == 'assigned' for order in plan.mrp_order_ids):
                plan.reservation_state = 'available'

    @api.depends('mrp_order_ids', 'mrp_order_ids.is_planned')
    def _compute_is_planned(self):
        for record in self:
            record.is_planned = all(mo.is_planned for mo in record.mrp_order_ids)

    @api.depends('mrp_order_ids')
    def _compute_move_byproduct_ids(self):
        for plan in self:
            byproduct_move_ids = []
            if plan.mrp_order_ids:
                for order in plan.mrp_order_ids:
                    for stock_move in order.move_finished_ids.filtered(lambda m: m.byproduct_id):
                        byproduct_move_ids.append(stock_move.id)
            plan.move_byproduct_ids = [(6, 0, byproduct_move_ids)]

    @api.depends('mo_stock_move_ids', 'mrp_order_ids.state', 'mo_stock_move_ids.product_uom_qty')
    def _compute_unreserve_visible(self):
        for plan in self:
            already_reserved = any(
                order.state not in ('done', 'cancel') for order in plan.mrp_order_ids) and plan.mapped(
                'mo_stock_move_ids.move_line_ids')
            any_quantity_done = any(m.quantity_done > 0 for m in plan.mo_stock_move_ids)

            plan.unreserve_visible = not any_quantity_done and already_reserved
            plan.reserve_visible = any(
                order.state in ('confirmed', 'progress', 'to_close') for order in plan.mrp_order_ids) and any(
                move.product_uom_qty and move.state in ['confirmed', 'partially_available'] for move in
                plan.mo_stock_move_ids)

    @api.depends('mrp_order_ids', 'mrp_order_ids.product_id')
    def _compute_product_ids(self):
        for record in self:
            record.product_ids = [(6, 0, record.mrp_order_ids.mapped('product_id').ids)]

    def _search_product_ids(self, operator, value):
        return [('mrp_order_ids.product_id', operator, value)]

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

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _default_mrp_plan_order_creation(self):
        result = self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_operations.mrp_plan_order_creation', default='auto_po_allow_manual')
        return result

    @api.model
    def _default_is_auto_create_production_order(self):
        mrp_plan_order_creation = self._default_mrp_plan_order_creation()
        return mrp_plan_order_creation in ('auto_po_allow_manual', 'auto_po_prohibit_manual')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approval', 'To be Approved '),
        ('approved', 'Approved'),
        ('reject', 'Rejected '),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done')
    ], default='draft', tracking=True)
    name = fields.Char(string='Plan Name', tracking=True)
    plan_id = fields.Char(string='Production Plan', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    priority = fields.Selection(
        PROCUREMENT_PRIORITIES, string='Priority', default='0', index=True, tracking=True)
    ppic_id = fields.Many2one('res.users', string='PPIC', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                             domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=True,
                             states={'draft': [('readonly', False)]}, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    create_uid = fields.Many2one(
        'res.users', string='Created By', default=lambda self: self.env.user, tracking=True)
    mrp_order_ids = fields.One2many('mrp.production', 'mrp_plan_id', string='Production Order',
                                    tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    mo_stock_move_ids = fields.One2many('stock.move', 'mrp_plan_id', string='Components',
                                        tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    workorder_ids = fields.One2many(
        'mrp.workorder', 'mrp_plan_id', string='Production Orders')
    move_byproduct_ids = fields.One2many(
        'stock.move', compute='_compute_move_byproduct_ids', tracking=True)

    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', readonly=True, copy=False)
    unreserve_visible = fields.Boolean('Allowed to Unreserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can unreserve')
    reserve_visible = fields.Boolean('Allowed to Reserve Production', compute='_compute_unreserve_visible',
        help='Technical field to check when we can reserve quantities')

    mrp_force_done = fields.Boolean(related="company_id.mrp_force_done", readonly=False)
    mo_force_done = fields.Boolean(related="company_id.mo_force_done", readonly=False)
    mp_auto_reserve_availability_materials = fields.Boolean('Auto reserve materials', related="company_id.mp_auto_reserve_availability_materials")

    date_planned_start = fields.Datetime('Scheduled Date Start', required=True, default=_get_default_date_planned_start)
    date_planned_finished = fields.Datetime('Scheduled Date Finished', required=True, default=_get_default_date_planned_finished)
    date_start = fields.Datetime('Actual Date', copy=False, index=True, readonly=True)
    date_finished = fields.Datetime('End Date', copy=False, index=True, readonly=True)
    
    reservation_state = fields.Selection(string='Reservation State', selection=[('waiting', 'Waiting for Material'), ('available', 'Material Available')], compute=_compute_reservation_state, store=True)
    is_planned = fields.Boolean(compute=_compute_is_planned)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    origin = fields.Char(
        'Source', copy=False,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document that generated this production plan request.")

    product_ids = fields.Many2many('product.product', string='Product', compute=_compute_product_ids, search=_search_product_ids)

    duration_expected = fields.Float('Expected Duration', compute=_compute_duration, help="Expected duration (in minutes)", store=False)
    duration = fields.Float('Actual Duration', compute=_compute_duration, store=False)
    is_user_working = fields.Boolean(compute=_compute_is_user_working)
    workorder_working_count = fields.Integer(compute=_compute_is_user_working)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    is_mr_done = fields.Boolean('Is Material Request Created', default=False)

    is_auto_create_production_order = fields.Boolean(string='Auto Create Production Order', default=_default_is_auto_create_production_order, readonly=True, states={'draft': [('readonly', False)]})
    mrp_plan_order_creation = fields.Selection(selection=[
        ('auto_po_allow_manual', 'Automatic Creation of Production Order and Allow Manual Creation'),
        ('manual_po_allow_auto', 'Manual Creation of Production Order and Allow Automatic Creation'),
        ('auto_po_prohibit_manual', 'Automatic Creation of Production Order, while Prohibiting Manual Creation'),
        ('manual_po_prohibit_auto', 'Manual Creation of Production Order, while Prohibiting Automatic Creation'),
    ], default=_default_mrp_plan_order_creation, string='Production Order Creation')

    line_ids = fields.One2many('mrp.plan.line', 'plan_id', string='To Produce', readonly=True)

    material_ids = fields.One2many('mrp.plan.material', 'plan_id', 'Predicted Materials', readonly=True)

    # unused fields, may delete someday
    mrp_submit_purchase_request = fields.Boolean(string='Allow Submit Purchase Request', related="company_id.mrp_submit_purchase_request", readonly=False)
    mrp_submit_material_request = fields.Boolean(string='Allow Submit Materials Request', related="company_id.mrp_submit_material_request", readonly=False)

    @api.onchange('date_planned_start')
    def _onchange_date_planned_start(self):
        # if self.date_planned_start and not self.is_planned:
        if self.date_planned_start:
            self.date_planned_finished = self.date_planned_start + timedelta(hours=1)
            self.mrp_order_ids.update({
                'date_planned_start': self.date_planned_start,
                'date_planned_finished': self.date_planned_finished
            })

    def button_plan(self):
        self.mrp_order_ids.button_plan()
        self._recompute_scheduled_date()

    def button_unplan(self):
        for production_id in self.mrp_order_ids:
            production_id.button_unplan()

        now = fields.Datetime.now()
        self.date_planned_start = now
        self.date_planned_finished = now + timedelta(hours=1)

    def button_unreserve(self):
        for plan in self:
            for order in plan.mrp_order_ids:
                order.button_unreserve()

    def action_confirm(self):
        self.ensure_one()
        if self.is_auto_create_production_order:
            for line in self.line_ids:
                line.action_confirm(to_produce_qty=line.to_produce_qty / line.no_of_mrp)

        self.mrp_order_ids.with_context(
            is_plan_autoreserve=self.env.company.mp_auto_reserve_availability_materials, 
            is_plan_allow_partial=self.env.company.mrp_plan_partial_availability
        ).action_confirm()
        self._recompute_scheduled_date()
        self.write({'state': 'confirm'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_add(self):
        view_id = self.env.ref('equip3_manuf_operations.manu_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Production Order'),
            'res_model': 'mrp.production.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {
                'default_plan_id': self.id,
                'default_branch_id': self.branch_id and self.branch_id.id or self.env.user.branch_id.id
            }
        }

    def action_check_availability(self):
        self.ensure_one()
        allow_partial = self.env.company.mrp_plan_partial_availability
        return self.mrp_order_ids.with_context(is_plan_allow_partial=allow_partial).action_assign(fill_with_available=True)

    def action_done(self):
        for plan in self:
            any_unfinished_wo = any(wo.state != 'done' for wo in plan.workorder_ids)
            if any_unfinished_wo:
                view_id = self.env.ref('equip3_manuf_operations.view_mp_done_confirm_wizard').id
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Confirm'),
                    'res_model': 'mp.done.confirm.wizard',
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[view_id, 'form']],
                    'context': {}
                }
            else:
                plan.mrp_order_ids.sudo().button_mark_done()
                plan.sudo().write({
                    'state': 'done',
                    'date_finished': max(plan.mrp_order_ids.mapped('date_finished'))
                })

    def _recompute_scheduled_date(self):
        self.ensure_one()
        date_planned_start = fields.Datetime.now()
        date_planned_finished = fields.Datetime.now() + relativedelta(hours=1)

        starts = self.mrp_order_ids.filtered(lambda w: w.date_planned_start)
        finished = self.mrp_order_ids.filtered(lambda w: w.date_planned_finished)
        sorted_starts = sorted(starts, key=lambda w: w.date_planned_start)
        sorted_finished = sorted(finished, key=lambda w: w.date_planned_finished)

        if sorted_starts:
            date_planned_start = sorted_starts[0].date_planned_start
            date_planned_finished = sorted_finished[-1].date_planned_finished

        self.write({
            'date_planned_start': date_planned_start,
            'date_planned_finished': date_planned_finished
        })

    # APPROVAL MATRIX
    # ==================================================================================================================
    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.manufacturing_plan_conf:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mrp.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'mp')
        ], limit=1).id

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = []
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'mp_id': record.id,
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

    is_matrix_on = fields.Boolean(related='company_id.manufacturing_plan_conf', string='Is Matric On')

    approval_matrix_id = fields.Many2one(
        comodel_name='mrp.approval.matrix', 
        domain="""[
            ('matrix_type', '=', 'mp'),
            ('branch_id', '=', branch_id),
            ('company_id', '=', company_id)
        ]""",
        string='Approval Matrix', 
        default=_default_approval_matrix)
    approval_matrix_line_ids = fields.One2many(
        comodel_name='mrp.approval.matrix.entry',
        inverse_name='mp_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)

    state_no_approval_matrix = fields.Selection(related='state', string='State No Approval Matrix')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)
    
    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.send_wa_approval_notification_mp
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
    @api.depends('labor_production_id')
    def _compute_labor_allowed_workorder_ids(self):
        for record in self:
            workorder_ids = record.labor_production_id.workorder_ids
            allowed_workorder_ids = workorder_ids.filtered(lambda w: w.state not in ('done', 'cancel'))
            record.labor_allowed_workorder_ids = [(6, 0, allowed_workorder_ids.ids)]

    @api.depends('labor_type', 'labor_production_id', 'labor_workorder_id', 'labor_group_id',
                 'labor_group_id.labor_ids', 'labor_ids')
    def _compute_labor_hide_assign_button(self):
        for record in self:
            err_message = record.check_action_assign_labor()
            record.labor_hide_assign_button = err_message is not False

    labor_allowed_workorder_ids = fields.One2many('mrp.workorder', compute=_compute_labor_allowed_workorder_ids)
    labor_type = fields.Selection(
        selection=[
            ('with_group', 'With Group'),
            ('without_group', 'Without Group')
        ],
        string='Labor Type', required=True, default='with_group', tracking=True)
    labor_production_id = fields.Many2one(
        'mrp.production', string='Labor Production Order', domain="[('id', 'in', mrp_order_ids)]", tracking=True)
    labor_workorder_id = fields.Many2one(
        'mrp.workorder', string='Labor Production Work Order', domain="[('id', 'in', labor_allowed_workorder_ids)]", tracking=True)
    labor_group_id = fields.Many2one('mrp.labor.group', string='Labor Group', tracking=True)
    labor_ids = fields.Many2many('hr.employee', string='Labor', domain="[('active', '=', True)]")
    labor_hide_assign_button = fields.Boolean(compute=_compute_labor_hide_assign_button)
    assign_ids = fields.One2many('mrp.labor.assign', 'plan_id', string='Assigned Labors')

    def reset_labor_form(self):
        self.ensure_one()
        return self.write({
            'labor_type': 'with_group',
            'labor_production_id': False,
            'labor_workorder_id': False,
            'labor_group_id': False,
            'labor_ids': [(5,)]
        })

    def check_action_assign_labor(self):
        self.ensure_one()
        err_message = False
        if not self.labor_production_id:
            err_message = _('Please select Production Order to assign!')
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

            labor_ids = record.labor_ids
            if record.labor_type == 'with_group':
                labor_ids = record.labor_group_id.labor_ids

            for labor in labor_ids:
                assign_labor.create({
                    'plan_id': record.id,
                    'production_id': record.labor_production_id.id,
                    'workorder_id': record.labor_workorder_id.id,
                    'labor_id': labor.id
                })
            record.reset_labor_form()

    def action_remove_labor(self):
        assign_to_delete = self.assign_ids.filtered(lambda a: a.workorder_id.state in ('pending', 'ready', 'cancel'))
        assign_to_delete.unlink()

    def _generate_pseudo_materials(self):
        self.ensure_one()
        plan_id = self.id

        material_values = [(5,)]
        for line in self.line_ids:
            line_id = line.line_id

            values = json.loads(line.bom_datas or '{}')
            if values:
                def _parent_produce(parent_id):
                    if line_id == parent_id:
                        return True
                    for v in values:
                        if v['line_id'] == parent_id:
                            return v['produce']
                    return False

                new_values = []
                for value in values:
                    parent_produce = _parent_produce(value['parent_id'])
                    if value['produce'] or (value['bom_id'] and parent_produce):
                        new_values += [value]

                values = new_values[:]
            else:
                values = []
                for i in range(line.no_of_mrp):
                    bom_product_qty = line.uom_id._compute_quantity(line.to_produce_qty, line.bom_id.product_uom_id)
                    values += line.bom_id._boom(bom_product_qty)

            for value in values:
                operation = self.env['mrp.routing.workcenter'].browse(value.get('operation_id', False))
                location =  operation._get_workcenter().location_id
                material_values += [(0, 0, {
                    'plan_id': plan_id,
                    'product_id': value.get('product_id', False),
                    'to_consume_qty': value.get('product_qty', 0.0),
                    'uom_id': value.get('product_uom', False),
                    'location_id': location.id
                })]
        self.material_ids = material_values


class MrpPlanLine(models.Model):
    _name = 'mrp.plan.line'
    _description = 'Production Plan Line'

    plan_id = fields.Many2one('mrp.plan', string='Production Plan', required=True, ondelete='cascade')
    sequence = fields.Integer(string='No.')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True)
    to_produce_qty = fields.Float(string='To Produce', digits='Product Unit of Measure')
    produced_qty = fields.Float(string='Produced', digits='Product Unit of Measure', compute='_compute_produced_qty')
    created_qty = fields.Float(string='Created Order', digits='Product Unit of Measure', compute='_compute_created_qty')
    remaining_qty = fields.Float(string='Remaining', digits='Product Unit of Measure', compute='_compute_remaining_qty')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    order_ids = fields.Many2many('mrp.production', string='Production Orders')
    no_of_mrp = fields.Integer(string='No of Manufacturing Order', default=1)
    
    # technical fields
    bom_line_id = fields.Many2one('mrp.bom.line')
    operation_id = fields.Many2one('mrp.routing.workcenter')
    bom_datas = fields.Text()
    line_id = fields.Integer()

    @api.depends('order_ids', 'order_ids.qty_produced', 'product_id')
    def _compute_produced_qty(self):
        for record in self:
            product = record.product_id
            record.produced_qty = sum(record.order_ids.filtered(lambda o: o.product_id == product).mapped('qty_produced'))

    @api.depends('order_ids', 'order_ids.product_uom_qty', 'product_id')
    def _compute_created_qty(self):
        for record in self:
            product = record.product_id
            record.created_qty = sum(record.order_ids.filtered(lambda o: o.product_id == product).mapped('product_qty'))

    @api.depends('to_produce_qty', 'created_qty')
    def _compute_remaining_qty(self):
        for record in self:
            record.remaining_qty = record.to_produce_qty - record.created_qty

    def action_create_production_order(self):
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_line_id': self.id})
        return {
            'name': _('Create Production Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'mrp.plan.line.wizard',
            'context': context
        }

    def action_confirm(self, to_produce_qty=None, no_of_order=None):
        self.ensure_one()
        if float_is_zero(self.remaining_qty, precision_rounding=self.uom_id.rounding):
            return

        if no_of_order is None:
            no_of_order = self.no_of_mrp

        if to_produce_qty is None:
            to_produce_qty = self.to_produce_qty

        plan = self.plan_id
        wizard_values = {
            'plan_id': plan.id,
            'line_ids': [(0, 0, {
                'line_id': self.line_id,
                'product_id': self.product_id.id,
                'bom_id': self.bom_id.id,
                'product_qty': to_produce_qty,
                'product_uom': self.uom_id.id,
                'no_of_mrp': no_of_order,
                'bom_line_id': self.bom_line_id.id,
                'operation_id': self.operation_id.id,
                'bom_datas': self.bom_datas
            })]
        }

        contexed_wizard = self.env['mrp.production.wizard'].with_context(
            active_model='mrp.plan',
            active_id=plan.id,
            active_ids=plan.ids,
        )

        order_values = []
        for i in range(int(no_of_order)):
            wizard = contexed_wizard.create(wizard_values)
            order_ids = wizard.with_context(skip_create_plan_line=True).confirm()

            if plan.state in ('confirm', 'progress'):
                order_ids.filtered(lambda o: o.state == 'draft').action_confirm()
            
            order_values += [(4, order.id) for order in order_ids]
        
        if order_values:
            self.order_ids = order_values
        if plan.state in ('confirm', 'progress'):
            plan._recompute_scheduled_date()


class MrpPlanMaterial(models.Model):
    _name = 'mrp.plan.material'
    _description = 'Production Plan Material'

    plan_id = fields.Many2one('mrp.plan', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    to_consume_qty = fields.Float(digits='Product Unit of Measure', string='To Consume')
    reserved_qty = fields.Float(digits='Product Unit of Measure', string='Reserved')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    location_id = fields.Many2one('stock.location', string='Production Location')
