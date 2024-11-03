# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProjectTaskStartStop(models.Model):
    _inherit = 'project.task'

    work_id = fields.One2many('task.work.history', 'task_id', string='Task Worked History')
    status = fields.Selection([('start', 'Start'), ('stop', 'Stop')], string='Status', default='stop', store=True)
    task_color = fields.Char(string='Kanban Color Index', related='company_id.task_color')

    def button_finish(self):
        if self.user_id != self.env.user and not self.user_has_groups('project.group_project_manager'):
            raise UserError(_('You can not Stop this task as this task is not assigned to you.'))
        work_id = self.env['task.work.history'].search([('task_id', 'in', self.ids), ('end_date', '=', False)])
        if work_id:
            tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
            work_id.end_date = datetime.now(tz).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.status = 'stop'
            analytic_account_id = self.env['account.analytic.line']
            analytic_account_id.create({
                    'name': work_id.description,
                    'project_id': self.project_id.id,
                    'task_id': self.id,
                    'account_id': self.project_id.analytic_account_id.id,
                    'unit_amount': work_id.duration,
                    })
            analytic_account_id.write({'task_id': analytic_account_id.id})

    def action_task_start(self):
        task_id = self.env['project.task'].search([('user_id', '=', self.env.user.id), ('status', '=', 'start')])
        if self.user_id != self.env.user and self.user_has_groups('project.group_project_manager'):
            raise UserError(_('You can not Start this task as this task is not assigned to you.'))
        if len(task_id) >= 1:
            if not self.user_has_groups('project_task_start_stop.group_work_multi_task'):
                raise UserError(_('You can not work on multiple task at a time, Please contact system Administrator to get access.'))
        view_id = self.env.ref('project_task_start_stop.project_task_description_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task Description'),
            'res_model': 'project.task.description',
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form,',
            'views': [[view_id, 'form']],
        }


class TaskWorkHistory(models.Model):
    _name = 'task.work.history'
    _description = "Task Work History"

    user_id = fields.Many2one('res.users', string="User")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    description = fields.Char(string="Description")
    duration = fields.Float(string='Work Hours', compute='_compute_duration', store=True)
    task_id = fields.Many2one('project.task', string='Project Task')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.end_date:
                d1 = fields.Datetime.from_string(blocktime.start_date)
                d2 = fields.Datetime.from_string(blocktime.end_date)
                diff = d2 - d1
                blocktime.duration = round(diff.total_seconds() / 3600.0, 2)
