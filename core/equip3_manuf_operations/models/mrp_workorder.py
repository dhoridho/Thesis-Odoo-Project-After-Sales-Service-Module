# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    @api.model
    def create(self, vals):
        vals['workorder_id'] = self.env['ir.sequence'].next_by_code('mrp.workorder')
        return super(MrpWorkorder, self).create(vals)

    def write(self, vals):
        if self.env.context.get('prevent_change_date_planned', False):
            if 'date_planned_start' in vals:
                del vals['date_planned_start']
            if 'date_planned_finished' in vals:
                del vals['date_planned_finished']
        
        if 'date_planned_start' in vals and not self.env.context.get('disable_auto_swap', False):
            dates_before = {}
            for wo in self:
                dates_before[wo] = (wo.date_planned_start, wo.date_planned_finished)

            res = super(MrpWorkorder, self).write(vals)

            workcenter_group = defaultdict(lambda: self.browse())
            for wo in self.filtered(lambda o: o.date_planned_start and o.date_planned_finished):
                workcenter_group[wo.workcenter_id] |= wo

            for workcenter, workorders in workcenter_group.items():
                wo_datas = {}
                for wo in workorders:
                    wo_datas[wo] = dates_before[wo]
                workcenter._swap_workorders(wo_datas)
        else:
            res = super(MrpWorkorder, self).write(vals)
        return res

    @api.depends('assign_ids', 'assign_ids.labor_id', 'assign_ids.labor_id.user_id')
    def _compute_wo_user_ids(self):
        for record in self:
            employee_ids = record.assign_ids.mapped('labor_id')
            user_ids = employee_ids.mapped('user_id') | self.env.user
            record.wo_user_ids = [(6, 0, user_ids.ids)]

    def _compute_working_users(self):
        for order in self:
            order.working_user_ids = [(4, order.id) for order in order.time_ids.filtered(lambda time: not time.date_end).sorted('date_start').mapped('user_id')]
            if order.working_user_ids:
                order.last_working_user_id = order.working_user_ids[-1]
            elif order.time_ids:
                order.last_working_user_id = order.time_ids.filtered('date_end').sorted('date_end')[-1].user_id if order.time_ids.filtered('date_end') else order.time_ids[-1].user_id
            else:
                order.last_working_user_id = False
            if order.time_ids.filtered(lambda x: (x.user_id.id in order.wo_user_ids.ids) and (not x.date_end) and (x.loss_type in ('productive', 'performance'))):
                order.is_user_working = True
            else:
                order.is_user_working = False

    def _compute_actual_date(self):
        for record in self:
            time_ids = record.time_ids
            record.actual_start_date = time_ids and time_ids[0].date_start or False
            record.actual_end_date = time_ids and time_ids[-1].date_end or False

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
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
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _compute_allowed_workcenters(self):
        all_workcenters = self.env['mrp.workcenter'].search([])
        for record in self:
            workcenter_ids = all_workcenters
            if record.operation_id.workcenter_type == 'with_group':
                workcenter_ids = record.workcenter_ids
            record.allowed_workcenter_ids = [(6, 0, workcenter_ids.ids)]

    def _action_confirm(self):
        super(MrpWorkorder, self)._action_confirm()
        workorders_by_production = defaultdict(lambda: self.env['mrp.workorder'])
        for workorder in self:
            workorders_by_production[workorder.production_id] |= workorder

        for production, workorders in workorders_by_production.items():
            if production.bom_operation_start_mode == 'flexible':
                workorders.state = 'ready'
    
    state = fields.Selection(selection_add=[
        ('pause', 'Paused'),
        ('block', 'Blocked'),
        ('done',)], string='Status',
        default='pending', copy=False, readonly=True)

    previous_state = fields.Char('Previous State')

    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'progress': [('readonly', True)]},
        group_expand='_read_group_workcenter_id', check_company=True)

    allowed_workcenter_ids = fields.Many2many('mrp.workcenter', string='Allowed Work Centers', compute=_compute_allowed_workcenters)

    location_id = fields.Many2one(
        'stock.location', 'Location',
        states={'done': [('readonly', True)], 'cancel': [
            ('readonly', True)], 'progress': [('readonly', True)]},
        check_company=True)

    # TODO: not sure why move_raw_ids & byproduct_ids replaced here
    move_raw_ids = fields.One2many('stock.move', 'mrp_workorder_component_id', 'Components')
    byproduct_ids = fields.One2many('stock.move', 'mrp_workorder_byproduct_id', 'By-Products')

    mrp_plan_id = fields.Many2one(related='production_id.mrp_plan_id', string='Production Plan', store=True)
    workorder_id = fields.Char(string='Workorder ID')
    company_id = fields.Many2one(related='production_id.company_id')
    branch_id = fields.Many2one(related='production_id.branch_id')

    actual_start_date = fields.Datetime('Actual Start Date', compute='_compute_actual_date')
    actual_end_date = fields.Datetime('Actual End Date', compute='_compute_actual_date')

    assign_ids = fields.One2many('mrp.labor.assign', 'workorder_id', string='Assigned Labors')
    wo_user_ids = fields.Many2many('res.users', compute=_compute_wo_user_ids, store=True)

    duration = fields.Float(string='Actual Duration')
    tool_ids = fields.One2many('mrp.bom.tools', 'workorder_id', string='Tools')
    workcenter_ids = fields.Many2many('mrp.workcenter', related='operation_id.workcenter_ids')

    bom_finished_type = fields.Selection(related='production_id.bom_finished_type')
    move_finished_only_ids = fields.One2many('stock.move', compute='_compute_move_finished_only')

    workcenter_domain = fields.Char(compute='_compute_workcenter_domain')

    @api.depends('operation_id')
    def _compute_workcenter_domain(self):
        for record in self:
            domain = []
            if record.operation_id.workcenter_type == 'with_group':
                domain = [('id', 'in', record.operation_id.workcenter_ids.ids)]
            record.workcenter_domain = json.dumps(domain)

    @api.depends('move_finished_ids')
    def _compute_move_finished_only(self):
        for workorder in self:
            workorder.move_finished_only_ids = workorder.move_finished_ids.filtered(lambda o: o.finished_id)

    def button_start(self):
        self = self.with_context(prevent_change_date_planned=True)
        result = super(MrpWorkorder, self).button_start()
        for workorder in self:
            if workorder.mrp_plan_id and workorder.mrp_plan_id.state != 'progress':
                workorder.mrp_plan_id.sudo().write({
                    'state': 'progress',
                    'date_start': workorder.production_id.date_start
                })
            if not workorder.production_id.date_start:
                if workorder.time_ids:
                    start = workorder.time_ids[0].date_start
                else:
                    start = fields.Datetime.now()
                workorder.production_id.write({'date_start': start})
        return result

    def button_finish(self):
        self = self.with_context(prevent_change_date_planned=True)
        result = super(MrpWorkorder, self).button_finish()
        for workorder in self:
            plan = workorder.mrp_plan_id
            if plan:
                any_unfinished_wos = any(wo.state != 'done' for wo in plan.workorder_ids)
                if not any_unfinished_wos and all(line.remaining_qty <= 0.0 for line in plan.line_ids):
                    plan.write({'state': 'to_close'})
        return result

    def button_pending(self):
        self.end_previous()
        return self.write({'state': 'pause'})

    def button_unblock(self):
        res = super(MrpWorkorder, self).button_unblock()
        work_order = self.env['mrp.workorder'].search([
            ('workcenter_id', '=', self.workcenter_id.id)
        ])
        for rec in work_order:
            if rec.state == 'block':
                rec.state = rec.previous_state
                rec.previous_state = ''
        return res

class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    def button_block(self):
        res = super(MrpWorkcenterProductivity, self).button_block()
        active_obj = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        work_order = self.env['mrp.workorder'].search([
            ('workcenter_id', '=', active_obj.workcenter_id.id),
            ('state', 'in', ['pause','progress', 'ready'])
        ])
        for rec in work_order:
            if rec.state in ['pause','progress', 'ready']:
                rec.previous_state = rec.state
                rec.state = 'block'
        return res
