# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError
from lxml import etree


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    
    # start_date = fields.Datetime(string="Scheduled Start Date", store="True")
    # end_date = fields.Datetime(string="Scheduled End Date", store="True")
    primary_status = fields.Selection(
        [('draft', 'Draft'),
         ('ready', 'Ready'), 
         ('waiting', 'Waiting for Another Job Order'), 
         ('in_progress', 'In Progress'), 
         ('complete', 'Complete'), 
         ('paused', 'Paused')], string="Status", readonly=True, default='draft')
    duration = fields.Float(string='Duration', default=0, compute='_compute_duration', inverse='_set_duration')
    time_ids = fields.One2many('hr.timesheet.time.progress', 'hr_timesheet_id')
    hr_working_duration = fields.Boolean(string='Working Duration')
    labour_amount = fields.Float(string='Labour Amount', store=True)
    labour_name = fields.Char(string='Labour', store=True)

    @api.model
    def create(self, vals):
        if vals.get('task_id'):
            task_state = vals.get('task_id.state')
            if task_state == 'draft':
                vals['primary_status'] = 'draft'
            elif task_state == 'inprogress':
                vals['primary_status'] = 'ready'
            else:
                vals['primary_status'] = 'draft'
        res = super(AccountAnalyticLine, self).create(vals)
        return res

    @api.depends('time_ids.duration')
    def _compute_duration(self):
        duration = 0.00
        for res in self:
            duration = res.duration = sum(res.time_ids.mapped('duration'))
            res.unit_amount = duration / 60

    def _prepare_timeline_vals(self, duration, date_start, date_end=False):
        return {
            'hr_timesheet_id': self.id,
            'date_start': date_start,
            'date_end': date_end,
        }
    
    def _set_duration(self):
        def _float_duration_to_second(duration):
            minutes = duration // 1
            seconds = (duration % 1) * 60
            return minutes * 60 + seconds

        for order in self:
            old_order_duation = sum(order.time_ids.mapped('duration'))
            new_order_duration = order.duration
            if new_order_duration == old_order_duation:
                continue

            delta_duration = new_order_duration - old_order_duation

            if delta_duration > 0:
                date_start = datetime.now() - timedelta(seconds=_float_duration_to_second(delta_duration))
                self.env['hr.timesheet.time.progress'].create(
                    order._prepare_timeline_vals(delta_duration, date_start, datetime.now())
                )
            else:
                duration_to_remove = abs(delta_duration)
                timelines = order.time_ids.sorted(lambda t: t.date_start)
                timelines_to_unlink = self.env['hr.timesheet.time.progress']
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

    def confirm(self):
        for res in self:
            res.write({
                'primary_status': 'ready',
            })

    def start(self):
        for res in self:
            res.write({
                'primary_status': 'in_progress',
                'hr_working_duration': True,
            })
            res.env['hr.timesheet.time.progress'].create(
                res._prepare_timeline_vals(res.duration, datetime.now())
            )
    
    def pause(self):
        for res in self:
            res.write({
                'primary_status': 'paused',
                'hr_working_duration': False,
            })
            time_ids = res.time_ids.filtered(lambda r:not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})

    def start_again(self):
        for res in self:
            res.write({
                'primary_status': 'in_progress',
                'hr_working_duration': True,
            })
            res.env['hr.timesheet.time.progress'].create(
                res._prepare_timeline_vals(res.duration, datetime.now())
            )

    def done(self):
        for res in self:
            res.write({
                'primary_status': 'complete',
                'hr_working_duration': False,
            })
            time_ids = res.time_ids.filtered(lambda r:not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})
            else:
                # raise ValidationError("At least one asset in allocation line")
                pass


class AssetTimeProgress(models.Model):
    _name = 'hr.timesheet.time.progress'
    _description = 'HR Timesheet Progress'

    hr_timesheet_id = fields.Many2one(comodel_name='account.analytic.line')
    date_start = fields.Datetime('Start Date', default=fields.Datetime.now, required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for res in self:
            if res.date_start and res.date_end:
                d1 = fields.Datetime.from_string(res.date_start)
                d2 = fields.Datetime.from_string(res.date_end)
                diff = d2 - d1
                res.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                res.duration = 0.0

    