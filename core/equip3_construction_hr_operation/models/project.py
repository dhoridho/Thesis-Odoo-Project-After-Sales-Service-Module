# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, _logger


class ProjectProject(models.Model):
    _inherit = 'project.project'

    custom_project_progress = fields.Selection(selection_add=[('timesheet', 'Hours Spent (Timesheet)')])
    allow_timesheets = fields.Boolean(
        "Timesheets", compute='_compute_allow_timesheets', store=True, readonly=True,
        default=False, help="Enable timesheeting on the project.")
    labour_cost_rate_ids = fields.One2many('labour.cost.rate', 'project_id', string='Labour Cost Rate')

    @api.onchange('working_hour_hours')
    def _onchange_working_hour(self):
        for rec in self:
            if rec.working_hour_hours > 24.00:
                raise ValidationError(_('Please enter working hour below 24 hours.'))
            rec.update({
                'working_hour': rec.working_hour_hours * 60,
            })

    # @api.depends('analytic_account_id')
    # def _compute_allow_timesheets(self):
    #     without_account = self.filtered(lambda t: not t.analytic_account_id and t._origin)
    #     without_account.update({'allow_timesheets': False})

    # @api.constrains('allow_timesheets', 'analytic_account_id')
    # def _check_allow_timesheet(self):
    #     for project in self:
    #         if project.allow_timesheets and not project.analytic_account_id:
    #             raise ValidationError(_('To allow timesheet, your project %s should have an analytic account set.', project.name))

    # @api.onchange('custom_project_progress')
    # def _onchange_custom_project_progress(self):
    #     for rec in self:
    #         if rec.custom_project_progress == 'timesheet':
    #             raise ValidationError(_('Please enable Timesheet in Project Settings to use this option.'))

    @api.depends('analytic_account_id', 'custom_project_progress')
    def _compute_allow_timesheets(self):
        for rec in self:
            if rec.custom_project_progress == 'timesheet':
                if not rec.analytic_account_id:
                    raise ValidationError(_('To allow timesheet, your project %s should have an analytic account set.', rec.name))
                else:
                    rec.write({'allow_timesheets': True,
                               'is_hide_allow_timesheets': False})
            else:
                rec.write({'allow_timesheets': False,
                           'is_hide_allow_timesheets': True})

    @api.onchange('custom_project_progress')
    def _onchange_custom_project_progress(self):
        for rec in self:
            task_ids = self.env['project.task'].search([('project_id', '=', rec.id)])
            if task_ids:
                raise ValidationError(_('Cannot change the "Progress Based On" because job order for this project has already been created.'))

                




