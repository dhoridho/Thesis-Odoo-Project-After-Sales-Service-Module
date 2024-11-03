from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from pytz import timezone
import json


class ProgressHistoryWizInherit(models.Model):
    _inherit = 'progress.history.wiz'

    current_total_duration = fields.Float(string='Current Total Duration')
    worker_ids = fields.Many2many('hr.employee', string='Worker')

    @api.onchange('list_work_order', 'list_sale_order', 'list_job_estimate', 'list_project_id')
    def _onchange_get_work_order(self):
        for rec in self:
            if rec.is_create_from_list_view:
                if rec.custom_project_progress == 'timesheet':
                    rec.update({
                        'progress_start_date_new': rec.list_work_order.start_time,
                        'progress_end_date_new': datetime.now(),
                        'current_total_duration': rec.list_work_order.work_hour_duration
                    })
        return super(ProgressHistoryWizInherit, self)._onchange_get_work_order()

    @api.onchange('labour_usage_ids')
    def _onchange_labour_usage_ids(self):
        for rec in self:
            if rec.project_id.custom_project_progress == 'timesheet':
                if rec.labour_usage_ids:
                    rec.worker_ids = rec.labour_usage_ids.mapped('workers_ids')
                else:
                    rec.worker_ids = False
            else:
                rec.worker_ids = False

    def get_timesheet_amount(self, duration, worker, labour):
        for rec in self:
            labour_usage_line = labour
            unit_price = labour_usage_line.unit_price
            amount = 0

            if labour_usage_line.uom_id.name == 'Days':
                amount = (duration / 60 / rec.project_id.working_hour_hours) * unit_price
            elif labour_usage_line.uom_id.name == 'Hours':
                amount = (duration / 60) * unit_price
            return amount

    def add_progress(self):
        for res in self:
            if res.project_id.custom_project_progress == 'timesheet':
                if res.work_order:
                    job_order = res.work_order
                else:
                    job_order = self.env['project.task'].browse(self.env.context.get('active_id'))

                attachment_line = []
                for attach in res.attachment_ids:
                    attachment_line.append(
                        (0, 0, {'date_now': attach.date_now,
                                'attachment': attach.attachment,
                                'name': attach.name,
                                'description': attach.description,
                                }
                         ))

                if not res.is_progress_history_approval_matrix:

                    if job_order.is_subtask == False:
                        if job_order.subtask_exist == False:
                            progress_line = res.env['progress.history'].sudo().create(res._prepare_vals_self_task(res, job_order, attachment_line))
                        else:
                            if not res.subtask:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line))
                            else:
                                task = res.subtask
                                subtask = res.subtask
                                progress = res.progress_subtask or res.progress
                                i = 0
                                while task:
                                    if not task.subtask_exist:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, task, attachment_line,
                                                                        progress, True))  # Bottom subtask
                                        i += 1

                                        progress = (progress * task.work_subtask_weightage) / 100
                                        res.env['progress.history'].sudo().create(
                                            res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                  subtask))  # Parent of bottom subtask
                                        if task.parent_task:
                                            task = task.parent_task
                                        else:
                                            break
                                    else:
                                        if task.is_subtask:
                                            if task.subtask_exist and res.subtask and i < 1:
                                                #selected subtask
                                                progress_line = res.env['progress.history'].sudo().create(
                                                    res._prepare_vals_self_task(res, task, attachment_line, progress, True))
                                                i += 1

                                            progress = (progress * task.work_subtask_weightage) / 100
                                            res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                      subtask))
                                            if task.parent_task:
                                                task = task.parent_task
                                            else:
                                                break
                                        else:
                                            progress = (progress * task.work_subtask_weightage) / 100
                                            res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                      subtask))
                                            break
                    else:
                        task = job_order
                        subtask = job_order
                        progress = res.progress_subtask or res.progress
                        i = 0
                        while task:
                            if not task.subtask_exist:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line, progress, True))#Bottom subtask
                                i+=1

                                progress = (progress * task.work_subtask_weightage) / 100
                                res.env['progress.history'].sudo().create(
                                    res._prepare_vals_parent_from_subtask(res, job_order, attachment_line, progress, subtask)) #Parent of bottom subtask
                                if task.parent_task:
                                    task = task.parent_task
                                else:
                                    break
                            else:
                                if task.is_subtask:
                                    if task.subtask_exist and not res.subtask and i <1:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, job_order, attachment_line,progress, True))
                                        i += 1

                                    progress = (progress * task.work_subtask_weightage) / 100
                                    res.env['progress.history'].sudo().create(res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress, subtask))
                                    if task.parent_task:
                                        task = task.parent_task
                                else:
                                    progress = (progress * task.work_subtask_weightage) / 100
                                    res.env['progress.history'].sudo().create(res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress, subtask))
                                    break

                    timesheet_vals = {
                        'date': datetime.now(),
                        'worker_ids': self.worker_ids.ids,
                        'start_date': res.progress_start_date_new,
                        'end_date': res.progress_end_date_new,
                        'duration': res.current_total_duration,
                        'name': res.progress_summary,
                    }

                    res.work_order.update({
                            'is_live': False,
                            'start_time': False,
                            'continue_time': False,
                            'is_pause': False,
                            'total_pause_duration': 0.0,
                            'pause_history_ids': [(5, 0, 0)],
                            'end_time': datetime.now(),
                            'timesheet_line_ids': [(0, 0, timesheet_vals)],
                        })

                    for labour in res.labour_usage_ids:
                        for worker in labour.workers_ids:
                            timesheet_analytic_vals = {
                                'date': datetime.now(),
                                'employee_id': worker.id,
                                'task_id': res.work_order.id,
                                'labour_name': labour.project_scope_id.name + " - " + labour.section_id.name + " - " + labour.product_id.name,
                                # 'worker_ids': self.worker_ids.ids,
                                'start_date': res.progress_start_date_new,
                                'end_date': res.progress_end_date_new,
                                'duration': res.current_total_duration,
                                'unit_amount': res.current_total_duration,
                                'labour_amount': res.get_timesheet_amount(res.current_total_duration, worker, labour),
                                'name': res.progress_summary,
                                'account_id': res.project_id.analytic_account_id.id,
                            }
                            self.env['account.analytic.line'].create(timesheet_analytic_vals)

                        cost_sheet = False
                        budget = False

                        duration = labour.progress_history_id.current_total_duration
                        time_left = 0
                        if labour.uom_id.name == 'Days':
                            duration += duration / 60 / labour.project_task_id.project_id.working_hour_hours
                        elif labour.uom_id.name == 'Hours':
                            duration += duration / 60

                        actual_used_time = duration
                        actual_used_amount = duration * labour.contractors * labour.unit_price

                        if labour.labour_usage_line_id.bd_labour_id:
                            labour.labour_usage_line_id.bd_labour_id.reserved_time -= actual_used_time
                            labour.labour_usage_line_id.bd_labour_id.amt_res -= actual_used_amount
                            labour.labour_usage_line_id.bd_labour_id.amt_used += actual_used_amount
                            labour.labour_usage_line_id.bd_labour_id.time_used += actual_used_time

                            if not budget:
                                budget = labour.labour_usage_line_id.bd_labour_id.budget_id
                        if labour.labour_usage_line_id.cs_labour_id:
                            labour.labour_usage_line_id.cs_labour_id.reserved_time -= actual_used_time
                            labour.labour_usage_line_id.cs_labour_id.reserved_amt -= actual_used_amount
                            labour.labour_usage_line_id.cs_labour_id.actual_used_amt += actual_used_amount
                            labour.labour_usage_line_id.cs_labour_id.actual_used_time += actual_used_time

                            if not cost_sheet:
                                cost_sheet = labour.labour_usage_line_id.cs_labour_id.job_sheet_id

                        if cost_sheet:
                            if cost_sheet.budgeting_method == 'gop_budget':
                                cost_sheet.get_gop_labour_table()
                        if budget:
                            if cost_sheet.budgeting_method == 'gop_budget':
                                budget.get_gop_labour_table()
                else:

                    # TO DO : Add multiple level subtask timesheet progress
                    # Only works on a parent task without any subtask
                    if len(res.approval_matrix_ids) == 0:
                        raise ValidationError(
                            _("There's no progress history approval matrix for this project or approval matrix default created. You have to create it first."))

                    if job_order.is_subtask == False:
                        if job_order.subtask_exist == False:
                            progress_line = res.env['progress.history'].sudo().create(
                                res._prepare_vals_self_task(res, job_order, attachment_line))
                            progress_line.write({'current_total_duration': res.current_total_duration,
                                                'worker_ids': res.worker_ids.ids
                                                 })

                            self.set_approval_values(job_order, progress_line)
                            self.set_message(job_order, progress_line)
                        else:
                            if not res.subtask:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line))
                                self.set_approval_values(job_order, progress_line)
                                self.set_message(job_order, progress_line)
                            else:
                                task = res.subtask
                                subtask = res.subtask
                                progress = res.progress_subtask or res.progress
                                progress_line = None
                                i = 0
                                while task:
                                    if not task.subtask_exist:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, task, attachment_line,
                                                                        progress, True))  # Bottom subtask
                                        self.set_approval_values(task, progress_line)
                                        i += 1

                                        progress = (progress * task.work_subtask_weightage) / 100
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                                  subtask))  # Parent of bottom subtask
                                        self.set_approval_values(task.parent_task, progress_line)
                                        self.set_message(task, progress_line)
                                        if task.parent_task:
                                            task = task.parent_task
                                        else:
                                            break
                                    else:
                                        if task.is_subtask:
                                            if task.subtask_exist and res.subtask and i < 1:
                                                # selected subtask
                                                progress_line = res.env['progress.history'].sudo().create(
                                                    res._prepare_vals_self_task(res, task, attachment_line, progress,
                                                                                True))
                                                self.set_approval_values(task, progress_line)
                                                self.set_message(task, progress_line)
                                                i += 1

                                            progress = (progress * task.work_subtask_weightage) / 100
                                            progress_line = res.env['progress.history'].sudo().create(
                                                res._prepare_vals_parent_from_subtask(res, task, attachment_line,
                                                                                      progress,
                                                                                      subtask))
                                            self.set_approval_values(task, progress_line)
                                            self.set_message(task, progress_line)
                                            if task.parent_task:
                                                task = task.parent_task
                                            else:
                                                break
                                        else:
                                            self.set_approval_values(task, progress_line)
                                            self.set_message(task, progress_line)
                                            break
                    else:
                        task = job_order
                        subtask = job_order
                        progress = res.progress_subtask or res.progress
                        progress_line = None
                        i = 0
                        while task:
                            if not task.subtask_exist:
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_self_task(res, job_order, attachment_line,
                                                                progress, True))  # Bottom subtask
                                self.set_approval_values(task, progress_line)
                                self.set_message(task, progress_line)
                                i += 1

                                progress = (progress * task.work_subtask_weightage) / 100
                                progress_line = res.env['progress.history'].sudo().create(
                                    res._prepare_vals_parent_from_subtask(res, job_order, attachment_line, progress,
                                                                          subtask))  # Parent of bottom subtask
                                self.set_approval_values(task.parent_task, progress_line)
                                # don't call self.set_message(task, progress_line) here
                                if task.parent_task:
                                    task = task.parent_task
                                else:
                                    break
                            else:
                                if task.is_subtask:
                                    if task.subtask_exist and not res.subtask and i < 1:
                                        progress_line = res.env['progress.history'].sudo().create(
                                            res._prepare_vals_self_task(res, job_order, attachment_line, progress,
                                                                        True))
                                        self.set_approval_values(task, progress_line)
                                        self.set_message(task, progress_line)
                                        i += 1

                                    progress = (progress * task.work_subtask_weightage) / 100
                                    progress_line = res.env['progress.history'].sudo().create(
                                        res._prepare_vals_parent_from_subtask(res, task, attachment_line, progress,
                                                                              subtask))
                                    self.set_approval_values(task, progress_line)
                                    self.set_message(task, progress_line)
                                    if task.parent_task:
                                        task = task.parent_task
                                else:
                                    self.set_approval_values(task, progress_line)
                                    self.set_message(task, progress_line)
                                    break

                    res.work_order.update({
                        'is_live': False,
                        'start_time': False,
                        'continue_time': False,
                        'is_pause': False,
                        'total_pause_duration': 0.0,
                        'pause_history_ids': [(5, 0, 0)],
                        'end_time': datetime.now(),
                    })

        return super(ProgressHistoryWizInherit, self).add_progress()

    @api.onchange('work_order')
    def _onchange_work_order(self):
        for rec in self:
            rec.update({
                'progress': rec.work_order.get_progress_hour_percentage(),
            })
        return {'domain': {'worker_ids': [('id', 'in', self.work_order.employee_worker_ids.ids)]}}


class ProgressHistoryInherit(models.Model):
    _inherit = 'progress.history'

    current_total_duration = fields.Float(string='Current Total Duration')
    worker_ids = fields.Many2many('hr.employee', string='Worker')

    def get_timesheet_amount(self, duration, worker, labour):
        for rec in self:
            labour_usage_line = labour
            unit_price = labour_usage_line.unit_price
            amount = 0

            if labour_usage_line.uom_id.name == 'Days':
                amount = (duration / 60 / rec.project_id.working_hour_hours) * unit_price
            elif labour_usage_line.uom_id.name == 'Hours':
                amount = (duration / 60) * unit_price
            return amount

    def update_labour_value_on_approval(self):
        res = super(ProgressHistoryInherit, self).update_labour_value_on_approval()
        for record in self:
            if record.custom_project_progress == 'timesheet':
                for labour in record.labour_usage_ids:
                    if record.work_order.is_subtask:
                        parent_task = record._get_subtask_parents()
                    else:
                        parent_task = record.work_order

                    if parent_task:
                        labour.labour_usage_line_id.write({
                            'time': labour.time,
                        })
                        subtasks = parent_task._get_subtask(depth=0)
                        # update all subtask usage
                        for subtask in subtasks:
                            labour_usage_line_id = subtask.labour_usage_ids.filtered(lambda
                                                                                         x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                            if labour_usage_line_id:
                                labour_usage_line_id.write({
                                    'time': labour.time,
                                })
                        # update parent usage
                        labour_usage_line_id = parent_task.labour_usage_ids.filtered(lambda
                                                                                         x: x.project_scope_id.id == labour.project_scope_id.id and x.section_id.id == labour.section_id.id and x.group_of_product_id.id == labour.group_of_product_id.id and x.product_id.id == labour.product_id.id)
                        if labour_usage_line_id:
                            labour_usage_line_id.write({
                                'time': labour.time,
                            })

                    cost_sheet = False
                    budget = False

                    duration = labour.progress_history_id.current_total_duration
                    time_left = 0
                    if labour.uom_id.name == 'Days':
                        duration += duration / 60 / labour.project_task_id.project_id.working_hour_hours
                    elif labour.uom_id.name == 'Hours':
                        duration += duration / 60

                    actual_used_time = duration
                    actual_used_amount = duration * labour.contractors * labour.unit_price

                    if labour.labour_usage_line_id.bd_labour_id:
                        labour.labour_usage_line_id.bd_labour_id.reserved_time -= actual_used_time
                        labour.labour_usage_line_id.bd_labour_id.amt_res -= actual_used_amount
                        labour.labour_usage_line_id.bd_labour_id.amt_used += actual_used_amount
                        labour.labour_usage_line_id.bd_labour_id.time_used += actual_used_time

                        if not budget:
                            budget = labour.labour_usage_line_id.bd_labour_id.budget_id
                    if labour.labour_usage_line_id.cs_labour_id:
                        labour.labour_usage_line_id.cs_labour_id.reserved_time -= actual_used_time
                        labour.labour_usage_line_id.cs_labour_id.reserved_amt -= actual_used_amount
                        labour.labour_usage_line_id.cs_labour_id.actual_used_amt += actual_used_amount
                        labour.labour_usage_line_id.cs_labour_id.actual_used_time += actual_used_time

                        if not cost_sheet:
                            cost_sheet = labour.labour_usage_line_id.cs_labour_id.job_sheet_id

                    if cost_sheet:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            cost_sheet.get_gop_labour_table()
                    if budget:
                        if cost_sheet.budgeting_method == 'gop_budget':
                            budget.get_gop_labour_table()
        return res

    def action_confirm_approving_matrix(self):
        if self.project_id.custom_project_progress == 'timesheet':
            sequence_matrix = [data.name for data in self.progress_history_user_ids]
            sequence_approval = [data.name for data in self.progress_history_user_ids.filtered(
                lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
            max_seq = max(sequence_matrix)
            min_seq = min(sequence_approval)
            approval = self.progress_history_user_ids.filtered(
                lambda line: self.env.user.id in line.user_ids.ids and len(
                    line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
            for record in self:

                    action_id = self.env.ref('equip3_construction_operation.action_view_task_inherited')
                    action_id_2 = self.env.ref('equip3_construction_operation.progress_history_action_approval')
                    template_app = self.env.ref('equip3_construction_operation.email_template_progress_history_approved')
                    template_app_2 = self.env.ref(
                        'equip3_construction_operation.email_template_progress_history_approved_original')
                    template_id = self.env.ref(
                        'equip3_construction_operation.email_template_reminder_for_progress_approval_temp')
                    template_id_2 = self.env.ref(
                        'equip3_construction_operation.email_template_reminder_for_progress_approval_temp_original')
                    user = self.env.user
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = base_url + '/web#id=' + str(record.work_order.id) + '&action=' + str(
                        action_id.id) + '&view_type=form&model=project.task'
                    url_2 = base_url + '/web#id=' + str(record.id) + '&action=' + str(
                        action_id_2.id) + '&view_type=form&model=progress.history'

                    current_user = self.env.uid
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"

                    if self.env.user not in record.approved_user_ids:
                        if record.is_approver:
                            for line in record.progress_history_user_ids:
                                for user in line.user_ids:
                                    if current_user == user.user_ids.id:
                                        line.timestamp = fields.Datetime.now()
                                        record.approved_user_ids = [(4, current_user)]
                                        var = len(line.approved_employee_ids) + 1
                                        if line.minimum_approver <= var:
                                            line.approver_state = 'approved'
                                            string_approval = []
                                            string_approval.append(line.approval_status)
                                            if line.approval_status:
                                                string_approval.append(f"{self.env.user.name}:Approved")
                                                line.approval_status = "\n".join(string_approval)
                                                string_timestammp = [line.approved_time]
                                                string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                                line.approved_time = "\n".join(string_timestammp)
                                            else:
                                                line.approval_status = f"{self.env.user.name}:Approved"
                                                line.approved_time = f"{self.env.user.name}:{dateformat}"
                                            line.is_approve = True
                                        else:
                                            line.approver_state = 'pending'
                                            string_approval = []
                                            string_approval.append(line.approval_status)
                                            if line.approval_status:
                                                string_approval.append(f"{self.env.user.name}:Approved")
                                                line.approval_status = "\n".join(string_approval)
                                                string_timestammp = [line.approved_time]
                                                string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                                line.approved_time = "\n".join(string_timestammp)
                                            else:
                                                line.approval_status = f"{self.env.user.name}:Approved"
                                                line.approved_time = f"{self.env.user.name}:{dateformat}"
                                        line.approved_employee_ids = [(4, current_user)]

                            matrix_line = sorted(record.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
                            progress = self.env['progress.history'].search([('progress_wiz', '=', record.progress_wiz.id)])
                            if len(matrix_line) == 0:
                                record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': record.employee_id.email,
                                    'date': date.today(),
                                    'work_order': self.work_order.name,
                                    'employee_id': self.employee_id.name,
                                    'code': self.number,
                                    'url': url,
                                    'url_2': url_2,
                                }
                                record.write({'state': 'approved',
                                              'approved_progress': record.progress})
                                record.update_labour_value_on_approval()

                                timesheet_vals = {
                                    'date': datetime.now(),
                                    'worker_ids': self.worker_ids.ids,
                                    'start_date': record.progress_start_date_new,
                                    'end_date': record.progress_end_date_new,
                                    'duration': record.current_total_duration,
                                    'name': record.progress_summary,
                                }

                                record.work_order.write({
                                    'is_live': False,
                                    'start_time': False,
                                    'continue_time': False,
                                    'is_pause': False,
                                    'total_pause_duration': 0.0,
                                    'pause_history_ids': [(5, 0, 0)],
                                    'end_time': datetime.now(),
                                    'timesheet_ids': [(0, 0, timesheet_vals)],
                                })

                                for labour in record.labour_usage_ids:
                                    for worker in labour.workers_ids:
                                        timesheet_analytic_vals = {
                                            'date': datetime.now(),
                                            'employee_id': worker.id,
                                            'task_id': record.work_order.id,
                                            'labour_name': labour.project_scope_id.name + " - " + labour.section_id.name + " - " + labour.product_id.name,
                                            # 'worker_ids': self.worker_ids.ids,
                                            'start_date': record.progress_start_date_new,
                                            'end_date': record.progress_end_date_new,
                                            'duration': record.current_total_duration,
                                            'unit_amount': record.current_total_duration,
                                            'labour_amount': record.get_timesheet_amount(record.current_total_duration,
                                                                                      worker, labour),
                                            'name': record.progress_summary,
                                            'account_id': record.project_id.analytic_account_id.id,
                                        }
                                        self.env['account.analytic.line'].create(timesheet_analytic_vals)

                                for rec in progress:
                                    rec.write({'state': 'approved',
                                               'approved_progress': rec.progress})
                                    template_app.sudo().with_context(ctx).send_mail(rec.work_order.id, True)
                                    template_app_2.sudo().with_context(ctx).send_mail(rec.id, True)

                            else:
                                record.last_approved = self.env.user.id
                                record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                                for approving_matrix_line_user in matrix_line[0].user_ids:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': approving_matrix_line_user.partner_id.email,
                                        'approver_name': approving_matrix_line_user.name,
                                        'date': date.today(),
                                        'submitter': record.last_approved.name,
                                        'code': self.number,
                                        'work_order': self.work_order.name,
                                        'url': url,
                                        'url_2': url_2,
                                    }
                                    for rec in progress:
                                        template_id.sudo().with_context(ctx).send_mail(rec.work_order.id, True)
                                        template_id_2.sudo().with_context(ctx).send_mail(rec.id, True)

                            job_id = self.work_order.id
                            action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
                            action['res_id'] = job_id
                            return action

                        else:
                            raise ValidationError(_(
                                'You are not allowed to perform this action!'
                            ))
                    else:
                        raise ValidationError(_(
                            'Already approved!'
                        ))

        return super(ProgressHistoryInherit, self).action_confirm_approving_matrix()


# Labour usage for progress history wizard
class ProgressLabourUsage(models.Model):
    _inherit = 'progress.labour.usage'

    def _compute_time_left(self):
        for rec in self:
            if not rec.is_add_progress:
                if rec.custom_project_progress == 'timesheet':
                    duration = rec.progress_history_id.current_total_duration
                    time_left = 0
                    if rec.uom_id.name == 'Days':
                        budgeted_duration = rec.temp_time_left * rec.project_task_id.project_id.working_hour_hours * 60
                        time_left += (budgeted_duration - duration) / 60 / rec.project_task_id.project_id.working_hour_hours
                    elif rec.uom_id.name == 'Hours':
                        budgeted_duration = rec.temp_time_left * 60
                        time_left += (budgeted_duration - duration) / 60

                    rec.time = time_left
                    rec.temp_time_left = time_left
            else:
                rec.time = rec.temp_time_left

            return super(ProgressLabourUsage, rec)._compute_time_left()


