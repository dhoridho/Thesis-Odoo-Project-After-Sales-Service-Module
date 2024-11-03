from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class ProjectTaskHR(models.Model):
    _inherit = 'project.task'

    start_time = fields.Datetime(string='Start Time')
    continue_time = fields.Datetime(string='Continue Time')
    end_time = fields.Datetime(string='End Time')

    custom_project_progress = fields.Selection(related='project_id.custom_project_progress', string='Project Progress')
    is_live = fields.Boolean(string='Is Live', default=False)
    is_pause = fields.Boolean(string='Is Pause', default=False)
    work_hour_duration = fields.Float(string='Duration', compute='_compute_work_hour_duration')
    total_pause_duration = fields.Float(string='Total Pause Duration')
    overtime_hours = fields.Float(string='Overtime Hours', compute='_compute_overtime_duration')
    pause_history_ids = fields.One2many('timer.pause.history', 'task_id', string='Pause History')
    timesheet_line_ids = fields.One2many('timesheet.line', 'task_id', string='Timesheet Line')
    planned_hours = fields.Float(compute='_compute_planned_hours')

    @api.depends('planned_end_date', 'planned_start_date')
    def _compute_planned_hours(self):
        for rec in self:
            if rec.custom_project_progress == 'timesheet':
                if rec.planned_end_date and rec.planned_start_date:
                    start_datetime = rec.planned_start_date
                    end_datetime = rec.planned_end_date
                    working_hour = (rec.project_id.working_hour_hours * 60)

                    if start_datetime.date() == end_datetime.date():
                        diff = end_datetime - start_datetime
                        total_duration = diff.total_seconds() / 60
                        if total_duration >= working_hour:
                            rec.planned_hours = working_hour
                        else:
                            rec.planned_hours = total_duration
                    else:
                        if rec.duration > 1:
                            total_duration = 0.0
                            if start_datetime:
                                temp_start_datetime = start_datetime
                                temp_end_datetime = start_datetime.replace(hour=23, minute=59, second=59)

                                diff = temp_end_datetime - temp_start_datetime
                                temp_total_duration = diff.total_seconds() / 60
                                if temp_total_duration >= working_hour:
                                    total_duration += working_hour
                                else:
                                    total_duration += temp_total_duration
                            if end_datetime:
                                temp_start_datetime = end_datetime.replace(hour=0, minute=0, second=0)
                                temp_end_datetime = end_datetime

                                diff = temp_end_datetime - temp_start_datetime
                                temp_total_duration = diff.total_seconds() / 60
                                if temp_total_duration >= working_hour:
                                    total_duration += working_hour
                                else:
                                    total_duration += temp_total_duration

                            temp_duration = rec.duration - 2

                            if temp_duration:
                                total_duration += temp_duration * working_hour
                            rec.planned_hours = total_duration
                        else:
                            total_duration = 0.0
                            if start_datetime:
                                temp_start_datetime = start_datetime
                                temp_end_datetime = start_datetime.replace(hour=23, minute=59, second=59)

                                diff = temp_end_datetime - temp_start_datetime
                                temp_total_duration = diff.total_seconds() / 60
                                if temp_total_duration >= working_hour:
                                    total_duration += working_hour
                                else:
                                    total_duration += temp_total_duration
                            if end_datetime:
                                temp_start_datetime = end_datetime.replace(hour=0, minute=0, second=0)
                                temp_end_datetime = end_datetime

                                diff = temp_end_datetime - temp_start_datetime
                                temp_total_duration = diff.total_seconds() / 60
                                if temp_total_duration >= working_hour:
                                    total_duration += working_hour
                                else:
                                    total_duration += temp_total_duration
                            rec.planned_hours = total_duration
                else:
                    rec.planned_hours = 0.0

            else:
                rec.planned_hours = 0.0

    def _compute_work_hour_duration(self):
        for rec in self:
            total_duration = 0.0
            if len(rec.pause_history_ids) > 0:
                if rec.is_pause:
                    total_duration = rec.total_pause_duration
                else:
                    total_duration = rec.total_pause_duration + (
                            datetime.now() - rec.continue_time).total_seconds() / 60
            else:
                if rec.start_time:
                    total_duration = (datetime.now() - rec.start_time).total_seconds() / 60
            rec.work_hour_duration = total_duration

    @api.depends('timesheet_line_ids.duration')
    def _compute_effective_hours(self):
        for task in self:
            task.effective_hours = sum(task.timesheet_line_ids.mapped('duration'))

    def _compute_overtime_duration(self):
        for rec in self:
            if rec.planned_hours > 0.0:
                if rec.effective_hours > rec.planned_hours:
                    rec.overtime_hours = rec.effective_hours - rec.planned_hours
                    rec.remaining_hours = 0.0
                else:
                    rec.overtime_hours = 0.0
            else:
                rec.overtime_hours = 0.0

    # @api.onchange('worker_assigned_to')
    # def _onchange_assigned_to(self):
    #     for rec in self:
    #         if rec.worker_assigned_to:
    #             rec.employee_worker_ids += rec.worker_assigned_to._origin

    @api.onchange('timesheet_line_ids')
    def _onchange_timesheet_line_ids(self):
        # Validation for delete if task is already done
        for rec in self:
            if not rec.is_subtask:
                if rec.state == 'complete':
                    current_timesheet_length = len(rec.timesheet_line_ids)
                    previous_timesheet_length = len(rec._origin.timesheet_line_ids._origin)

                    if current_timesheet_length < previous_timesheet_length:
                        raise ValidationError(_("You cannot delete timesheet line because task is already done."))
            else:
                if rec.parent_task.state == 'complete' or rec.state == 'complete':
                    current_timesheet_length = len(rec.timesheet_line_ids)
                    previous_timesheet_length = len(rec._origin.timesheet_line_ids._origin)

                    if current_timesheet_length < previous_timesheet_length:
                        raise ValidationError(_("You cannot delete timesheet line because task is already done."))

    def start_work_hour(self):
        for rec in self:
            if rec.state != 'inprogress':
                raise ValidationError(
                    _("Cannot add progress when state is not in 'Progress'.\nClick In Progress button first"))

            if rec.actual_start_date:
                if rec.actual_start_date > datetime.now():
                    raise ValidationError(_("Progress Start Date should be after Actual Start Date."))
                else:
                    rec.update({
                        'start_time': datetime.now(),
                        'is_live': True,
                    })

    def pause_work_hour(self):
        for rec in self:
            if rec.continue_time:
                vals = {
                    'start_time': rec.continue_time,
                    'pause_time': datetime.now(),
                }
            else:
                vals = {
                    'start_time': rec.start_time,
                    'pause_time': datetime.now(),
                }
            rec.update({
                'is_pause': True,
                'pause_history_ids': [(0, 0, vals)],
            })

            if len(rec.pause_history_ids) > 0:
                pause_duration = 0.0
                for pause in rec.pause_history_ids:
                    pause_duration += pause.duration
                rec.total_pause_duration = pause_duration

    def continue_work_hour(self):
        for rec in self:
            rec.update({
                'continue_time': datetime.now(),
                'is_pause': False,
            })

    def get_progress_hour_percentage(self):
        for task in self:
            if task.planned_hours > 0.0:
                # TO DO : Add multiple level subtask effective hours
                return round(100.0 * task.work_hour_duration / task.planned_hours, 2)
            else:
                return 0

    def end_work_hour(self):
        self._compute_work_hour_duration()
        if self.custom_project_progress == 'timesheet':
            progress_ids = self.progress_history_ids.filtered(
                lambda f: f.state in ['draft', 'to_approve'])
            if len(progress_ids) > 0:
                raise ValidationError(
                    _("Cannot add progress anymore because request status waiting for approval in progress history."))

            if self.state != 'inprogress':
                raise ValidationError(
                    _("Cannot add progress when state is not in 'Progress'.\nClick In Progress button first"))
            elif self.progress_task == 100:
                raise ValidationError(
                    _("Cannot add progress anymore because the progress of this job order is already 100%"))
            else:
                self._compute_work_hour_duration()
                progress_history = {'default_work_order': self.id,
                                    'default_name': self.name,
                                    'default_progress': self.get_progress_hour_percentage(),
                                    'default_current_total_duration': self.work_hour_duration,
                                    'default_project_id': self.project_id.id,
                                    'default_sale_order': self.sale_order.id,
                                    'default_purchase_subcon': self.purchase_subcon.id,
                                    'default_completion_ref': self.completion_ref.id,
                                    'default_stage_new': self.stage_new.id,
                                    'default_is_subcon': self.is_subcon,
                                    'default_is_subtask': self.is_subtask,
                                    'default_subtask_exist': self.subtask_exist,
                                    'default_job_estimate': self.job_estimate.id,
                                    'default_branch_id': self.branch_id.id,
                                    'default_parent_task': self.parent_task.id,
                                    'default_progress_start_date_new': self.start_time,
                                    'default_progress_end_date_new': datetime.now(),
                                    'default_worker_ids': [(6, 0, self.labour_usage_ids.mapped('workers_ids').ids)],
                                    'default_labour_usage_ids': self.get_labour_usage(),
                                    }

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'progress.history.wiz',
                    'name': _("Create Progress History"),
                    "context": progress_history,
                    'target': 'new',
                    'view_mode': 'form',
                }


class TimerPauseHistory(models.Model):
    _name = 'timer.pause.history'
    _description = ('Timesheet TImer Pause History (Following data of pause time will be stored here and not visible '
                    'to user)')

    task_id = fields.Many2one('project.task', string='Task')
    start_time = fields.Datetime(string='Start Time')
    pause_time = fields.Datetime(string='Pause Time')
    duration = fields.Float(string='Duration', compute='_compute_duration')

    @api.depends('start_time', 'pause_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.pause_time:
                rec.duration = (rec.pause_time - rec.start_time).total_seconds() / 60
            else:
                rec.duration = 0.0


class TimesheetInherit(models.Model):
    _inherit = 'account.analytic.line'

    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')


class TimesheetLine(models.Model):
    _name = 'timesheet.line'
    _description = 'Timesheet Line'

    name = fields.Char(string='Description')
    date = fields.Date(string='Date')
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', string='Company')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    worker_ids = fields.Many2many('hr.employee', string='Worker')
    duration = fields.Float(string='Duration')

    def unlink(self):
        for rec in self:
            if rec.task_id:
                if rec.task_id.is_subtask:
                    if rec.task_id.parent_task:
                        if rec.task_id.parent_task.state == 'complete' or rec.task_id.state == 'complete':
                            raise ValidationError(_("You cannot delete timesheet line because task is already done."))
                else:
                    if rec.task_id.state == 'complete':
                        raise ValidationError(_("You cannot delete timesheet line because task is already done."))
        return super(TimesheetLine, self).unlink()
