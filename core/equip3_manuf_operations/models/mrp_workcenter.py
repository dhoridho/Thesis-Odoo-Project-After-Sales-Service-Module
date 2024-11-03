from odoo import models, fields, api, _
from functools import partial
from datetime import timedelta
from pytz import timezone
from odoo.addons.resource.models.resource import make_aware, Intervals
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.addons.mrp.models.mrp_workcenter import MrpWorkcenter as BasicMrpWorkcenter


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    def _register_hook(self):
        BasicMrpWorkcenter._patch_method('_get_first_available_slot', _get_first_available_slot)
        return super(MrpWorkcenter, self)._register_hook()

    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('waiting', 'Waiting'),
            ('running', 'Running'),
            ('blocked', 'Blocked')
        ], string='Status', compute='_compute_state'
    )
    running_workorders_count = fields.Integer(compute='_compute_state')
    waiting_workorders_count = fields.Integer(compute='_compute_state')
    loss_id = fields.Many2one('mrp.workcenter.productivity.loss', "Loss Reason")
    description = fields.Text('Description')
    note = fields.Text(string='Notes')
    labor_ids = fields.One2many('mrp.workcenter.labor', 'workcenter_id', string='Labors')

    @api.depends('time_ids', 'time_ids.date_end', 'time_ids.loss_type')
    def _compute_working_state(self):
        for workcenter in self:
            time_log = self.env['mrp.workcenter.productivity'].search([
                ('workcenter_id', '=', workcenter.id),
                ('date_end', '=', False)
            ], limit=1)
            if not time_log:
                if workcenter.working_state == 'normal':
                    workcenter.working_state = 'blocked'
                else:
                    workcenter.working_state = 'normal'
            elif time_log.loss_type in ('productive', 'performance'):
                workcenter.working_state = 'done'
            else:
                workcenter.working_state = 'blocked'

    @api.model
    def action_production_view(self, workcenter_id):
        action = self.env.ref('mrp.mrp_workorder_todo').read()[0]
        action['domain'] = [('workcenter_id', '=', workcenter_id)]
        return action
    
    def _compute_state(self):
        for record in self:
            running_count = 0
            waiting_count = 0
            if record.working_state == 'blocked':
                state = 'blocked'
            else:
                order_ids = record.order_ids
                progress_workorders = order_ids.filtered(lambda w: w.state == 'progress')
                if progress_workorders:
                    state = 'running'
                    running_count = len(progress_workorders)
                else:
                    scheduled_workorders = order_ids.filtered(
                        lambda w: w.state in ('pending', 'ready') and w.date_planned_start is not False)
                    if scheduled_workorders:
                        state = 'waiting'
                        waiting_count = len(scheduled_workorders)
                    else:
                        state = 'available'
            record.state = state
            record.running_workorders_count = state == 'running' and running_count or 0
            record.waiting_workorders_count = state == 'waiting' and waiting_count or 0

    def unblock(self):
        res = super(MrpWorkcenter, self).unblock()
        self.write({
            'loss_id': False,
            'description': False
        })
        return res

    def _swap_workorders(self, wo_datas):
        self.ensure_one()

        def update_dates(workorder, start_date):
            workcenter = workorder.workcenter_id
            duration_expected = workorder.duration_expected
            from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
            if not from_date:
                raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))

            if workorder.leave_id:
                workorder.leave_id.unlink()
            
            leave = self.env['resource.calendar.leaves'].create({
                'name': workorder.display_name,
                'calendar_id': workcenter.resource_calendar_id.id,
                'date_from': from_date,
                'date_to': to_date,
                'resource_id': workcenter.resource_id.id,
                'time_type': 'other'
            })
            workorder.with_context(disable_auto_swap=True).write({'leave_id': leave.id})

        orders = self.order_ids.filtered(lambda o: o not in wo_datas and o.date_planned_start and o.date_planned_finished)

        overlaps = defaultdict(lambda: self.env['mrp.workorder'])
        for wo, (start, stop) in wo_datas.items():
            for order in orders:
                is_overlap = order.date_planned_start < wo.date_planned_finished and order.date_planned_finished > wo.date_planned_start
                if is_overlap:
                    overlaps[wo] |= order

        if not overlaps:
            for wo, (start, stop) in wo_datas.items():
                wo.leave_id.unlink()
                update_dates(wo, wo.date_planned_start)
        else:
            for wo, overlap_orders in overlaps.items():
                (wo | overlap_orders).leave_id.unlink()
            
            for wo, overlap_orders in overlaps.items():
                update_dates(wo, min(overlap_orders.mapped('date_planned_start')))
                next_date_planned_start = wo.date_planned_finished

                for order in overlap_orders:
                    update_dates(order, next_date_planned_start)
                    next_date_planned_start = order.date_planned_finished

class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    def button_block(self):
        res = super(MrpWorkcenterProductivity, self).button_block()
        self.workcenter_id.write({
            'loss_id': self.loss_id.id,
            'description': self.description
        })


class MrpWorkcenterLabor(models.Model):
    _name = 'mrp.workcenter.labor'
    _description = 'Workcenter Labor'
    _rec_name = 'user_id'

    workcenter_id = fields.Many2one('mrp.workcenter', string='Workcenter', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Labor', required=True)


"""
[FIX] mrp_workorder: calculate correctly the WO scheduled end date
https://github.com/odoo/odoo/commit/b02cdbbe36ead262331fc74ec3039c8ded313d3d
"""
def _get_first_available_slot(self, start_datetime, duration):
    """Get the first available interval for the workcenter in `self`.

    The available interval is disjoinct with all other workorders planned on this workcenter, but
    can overlap the time-off of the related calendar (inverse of the working hours).
    Return the first available interval (start datetime, end datetime) or,
    if there is none before 700 days, a tuple error (False, 'error message').

    :param start_datetime: begin the search at this datetime
    :param duration: minutes needed to make the workorder (float)
    :rtype: tuple
    """
    self.ensure_one()
    start_datetime, revert = make_aware(start_datetime)

    get_available_intervals = partial(self.resource_calendar_id._work_intervals, domain=[('time_type', 'in', ['other', 'leave'])], resource=self.resource_id, tz=timezone(self.resource_calendar_id.tz))
    get_workorder_intervals = partial(self.resource_calendar_id._leave_intervals, domain=[('time_type', '=', 'other')], resource=self.resource_id, tz=timezone(self.resource_calendar_id.tz))

    remaining = duration
    start_interval = start_datetime
    delta = timedelta(days=14)

    for n in range(50):  # 50 * 14 = 700 days in advance (hardcoded)
        dt = start_datetime + delta * n
        available_intervals = get_available_intervals(dt, dt + delta)
        workorder_intervals = get_workorder_intervals(dt, dt + delta)
        for start, stop, dummy in available_intervals:
            # Shouldn't loop more than 2 times because the available_intervals contains the workorder_intervals
            # And remaining == duration can only occur at the first loop and at the interval intersection (cannot happen several time because available_intervals > workorder_intervals
            for i in range(2):
                interval_minutes = (stop - start).total_seconds() / 60
                # If the remaining minutes has never decrease update start_interval
                if remaining == duration:
                    start_interval = start
                # If there is a overlap between the possible available interval and a others WO
                if Intervals([(start_interval, start + timedelta(minutes=min(remaining, interval_minutes)), dummy)]) & workorder_intervals:
                    remaining = duration
                elif float_compare(interval_minutes, remaining, precision_digits=3) >= 0:
                    return revert(start_interval), revert(start + timedelta(minutes=remaining))
                else:
                    # Decrease a part of the remaining duration
                    remaining -= interval_minutes
                    # Go to the next available interval because the possible current interval duration has been used
                    break
    return False, 'Not available slot 700 days after the planned start'
