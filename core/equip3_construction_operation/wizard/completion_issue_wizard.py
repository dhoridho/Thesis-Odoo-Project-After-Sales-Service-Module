from odoo import models, fields, api, _
from datetime import datetime, date
from datetime import timedelta


class CompletionIssueWizard(models.TransientModel):
    '''All project task completion issue related to predecessor and successor will be handled in this wizard'''
    _name = 'completion.issue.wizard'
    _description = 'Project Task Completion Issues'

    project_task_id = fields.Many2one('project.task', string='Project Task')
    warning_top = fields.Html(string='Warning',
                              default="These tasks are in conflict. Please select the action you would like to take.",
                              readonly=True)
    warning_bottom = fields.Html(string='Warning',
                                 default="If you would like to force current task only, please click this button.",
                                 readonly=True)
    actual_end_date = fields.Datetime(string='Actual End Date')
    issue_ids = fields.One2many('completion.issue', 'completion_issue_wizard_id', string='Completion Issues')
    issues_solved = fields.Boolean(string='Issues Solved', default=False, compute='_compute_issues_solved')

    @api.depends('issue_ids')
    def _compute_issues_solved(self):
        for record in self:
            check_issue = list()
            for issue in record.issue_ids:
                check_issue.append(issue.is_solved)
            if False not in check_issue:
                record.issues_solved = True
            else:
                record.issues_solved = False

    def check_all_time_conflict(self):
        for issue in self.issue_ids:
            if issue.is_time_conflict == False:
                return False
        return True

    def force_complete(self, task):
        task.write({'state': 'complete',
                    'progress_task': 100,
                    'actual_end_date': self.actual_end_date,
                    'purchase_order_exempt': False
                    })
        return True

    def force_confirm(self, task):
        labour_usages = []
        task.write({
            'state': 'inprogress',
            'purchase_order_exempt': False,
            'actual_start_date': datetime.now()
        })
        if not task.project_id.act_start_date:
            task.project_id.write({'act_start_date': task.actual_start_date.date()})
        if not task.is_subtask:
            cost_sheet = False
            project_budget = False
            for labour in task.labour_usage_ids:
                labour.cs_labour_id.write({
                    'reserved_time': labour.cs_labour_id.reserved_time + labour.time,
                    'reserved_amt': labour.cs_labour_id.reserved_amt + (
                            labour.contractors * labour.unit_price * labour.time),
                    'reserved_contractors': labour.cs_labour_id.reserved_contractors + labour.contractors
                })
                if not cost_sheet:
                    cost_sheet = labour.cs_labour_id.job_sheet_id
                if labour.bd_labour_id:
                    labour.bd_labour_id.write({
                        'reserved_time': labour.bd_labour_id.reserved_time + labour.time,
                        'amt_res': labour.bd_labour_id.amt_res + (
                                labour.contractors * labour.unit_price * labour.time),
                        'reserved_contractors': labour.bd_labour_id.reserved_contractors + labour.contractors
                    })
                    if not project_budget:
                        project_budget = labour.bd_labour_id.budget_id
                if labour.workers_ids:
                    labour_usages.append(labour)
            if cost_sheet:
                cost_sheet.get_gop_labour_table()
            if project_budget:
                project_budget.get_gop_labour_table()
            return labour_usages
        return []

    def action_force_start_and_complete(self):
        # Force all action available in view to be executed
        if self.check_all_time_conflict():
            # If all issue left are time conflict, then complete the task
            return self.action_done()
        else:
            for issue in self.issue_ids:
                if issue.type == 'FF':
                    if issue.parent_task_id.state == 'draft':
                        # issue.parent_task_id.write({
                        #     'state': 'inprogress',
                        #     'purchase_order_exempt': False,
                        #     'actual_start_date': datetime.now()})
                        self.force_confirm(issue.parent_task_id)
                        issue.write({
                            'is_draft': False,
                            'actual_start_date': datetime.now(),
                            'reason': 'Predecessor task progress is %s' % (issue.parent_task_id.progress_task) + '%',
                        })
                    elif issue.parent_task_id.state == 'inprogress':
                        # issue.parent_task_id.write({'state': 'complete', 'progress_task': 100,
                        #                             'actual_end_date': self.actual_end_date,
                        #                             'purchase_order_exempt': False})
                        self.force_complete(issue.parent_task_id)

                        if issue.parent_task_id.actual_end_date:
                            actual_end_date = False
                            if issue.lag_type == 'day':
                                actual_end_date = issue.parent_task_id.actual_end_date + timedelta(days=issue.lag_qty)
                            elif issue.lag_type == 'hour':
                                actual_end_date = issue.parent_task_id.actual_end_date + timedelta(hours=issue.lag_qty)
                            elif issue.lag_type == 'minute':
                                actual_end_date = issue.parent_task_id.actual_end_date + timedelta(
                                    minutes=issue.lag_qty)

                            if issue.parent_task_id.actual_end_date < actual_end_date:
                                issue.write({'is_time_conflict': True,
                                             'reason': 'Predecessor actual end date conflicted with task\'s time lag'})
                            else:
                                issue.write({'is_solved': True,
                                             'actual_end_date': self.actual_end_date,
                                             'reason': 'Solved'})
                elif issue.type == 'SF':
                    if issue.parent_task_id.state == 'draft':
                        # issue.parent_task_id.write({
                        #     'state': 'inprogress',
                        #     'purchase_order_exempt': False,
                        #     'actual_start_date': datetime.now()
                        # })
                        self.force_confirm(issue.parent_task_id)

                        if issue.parent_task_id.actual_start_date:
                            lag_start_date = False
                            if issue.lag_type == 'day':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(days=issue.lag_qty)
                            elif issue.lag_type == 'hour':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(hours=issue.lag_qty)
                            elif issue.lag_type == 'minute':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(
                                    minutes=issue.lag_qty)

                            if self.actual_end_date < lag_start_date:
                                issue.write({'is_time_conflict': True,
                                             'actual_start_date': datetime.now(),
                                             'reason': 'Task\'s actual end date conflicted with predecessor\'s time lag'})
                            else:
                                issue.write({
                                    'is_draft': False,
                                    'is_solved': True,
                                    'actual_start_date': datetime.now(),
                                    'reason': 'Solved',
                                })

            # If all issues are solved, then complete current task
            if self.issues_solved:
                return self.action_done()
            else:
                return {
                    'name': _('Confirmation'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'view_id': self.env.ref('equip3_construction_operation.completion_issue_view_form').id,
                    'target': 'new',
                    'res_model': 'completion.issue.wizard',
                    'res_id': self.id,
                }

    def action_force_complete_current(self):
        # return self.project_task_id.write({
        #     'progress_task': 100,
        #     'state': 'complete',
        #     'actual_end_date': self.actual_end_date,
        #     'purchase_order_exempt': False
        # })
        self.force_complete(self.project_task_id)

    def action_done(self):
        # return self.project_task_id.write({
        #     'progress_task': 100,
        #     'state': 'complete',
        #     'actual_end_date': self.actual_end_date,
        #     'purchase_order_exempt': False
        # })
        self.force_complete(self.project_task_id)

    def action_cancel(self):
        return self.project_task_id.write({
            'state': 'inprogress',
            'purchase_order_exempt': False
        })


class Issue(models.TransientModel):
    _name = 'completion.issue'
    _description = 'Project Task Completion Issue'

    project_task_id = fields.Many2one('project.task', string='Project Task')
    completion_issue_wizard_id = fields.Many2one('completion.issue.wizard', string='Completion Issue Wizard')
    parent_task_id = fields.Many2one('project.task', string='Job order')
    actual_start_date = fields.Datetime(string='Actual Start Date')
    actual_end_date = fields.Datetime(string='Actual End Date')
    type = fields.Selection([('FF', 'Finish to Finish'), ('FS', 'Finish to Start'), ('SF', 'Start to Finish')],
                            string='Type')
    lag_qty = fields.Integer(string='Lag')
    lag_type = fields.Selection([('day', 'Day'), ('hour', 'Hour'), ('minute', 'Minute')], string='Lag Type')
    reason = fields.Text(string='Reason')
    is_draft = fields.Boolean(string='Is Draft', default=False)
    is_solved = fields.Boolean(string='Issue Solved', default=False)
    is_time_conflict = fields.Boolean(string='Is Time Conflict', default=False)

    def button_force_complete(self):
        # self.parent_task_id.write({'state': 'complete',
        #                            'progress_task': 100,
        #                            'actual_end_date': self.completion_issue_wizard_id.actual_end_date,
        #                            'purchase_order_exempt': False
        #                            })
        self.completion_issue_wizard_id.force_complete(self.parent_task_id)

        if self.parent_task_id.actual_end_date:
            lag_end_date = False
            if self.lag_type == 'day':
                lag_end_date = self.parent_task_id.actual_end_date + timedelta(days=self.lag_qty)
            elif self.lag_type == 'hour':
                lag_end_date = self.parent_task_id.actual_end_date + timedelta(hours=self.lag_qty)
            elif self.lag_type == 'minute':
                lag_end_date = self.parent_task_id.actual_end_date + timedelta(minutes=self.lag_qty)

            if self.type == 'FF':
                if self.parent_task_id.actual_end_date <= lag_end_date:
                    self.write({'is_draft': False,
                                'is_time_conflict': True,
                                'actual_end_date': self.completion_issue_wizard_id.actual_end_date,
                                'reason': 'Predecessor actual end date conflicted with task\'s time lag'})
                else:
                    self.write({'is_solved': True,
                                'actual_end_date': self.completion_issue_wizard_id.actual_end_date,
                                'reason': 'Solved'
                                })

        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_operation.completion_issue_view_form').id,
            'target': 'new',
            'res_model': 'completion.issue.wizard',
            'res_id': self.completion_issue_wizard_id.id,
        }

    def button_force_start(self):
        if self.type == 'FF':
            # self.parent_task_id.write({
            #     'state': 'inprogress',
            #     'purchase_order_exempt': False,
            #     'actual_start_date': datetime.now()
            # })
            self.completion_issue_wizard_id.force_confirm(self.parent_task_id)
            self.write({
                'is_draft': False,
                'actual_start_date': datetime.now(),
                'reason': 'Predecessor task progress is %s' % (self.parent_task_id.progress_task) + '%',
            })
        elif self.type == 'SF':
            # self.parent_task_id.write({
            #     'state': 'inprogress',
            #     'purchase_order_exempt': False,
            #     'actual_start_date': datetime.now()
            # })
            self.completion_issue_wizard_id.force_confirm(self.parent_task_id)

            if self.parent_task_id.actual_start_date:
                lag_start_date = False
                if self.lag_type == 'day':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(days=self.lag_qty)
                elif self.lag_type == 'hour':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(hours=self.lag_qty)
                elif self.lag_type == 'minute':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(minutes=self.lag_qty)

                if self.completion_issue_wizard_id.actual_end_date < lag_start_date:
                    self.write({'is_draft': False,
                                'is_time_conflict': True,
                                'actual_start_date': datetime.now(),
                                'reason': 'Task\'s actual end date conflicted with predecessor\'s time lag'})
                else:
                    self.write({
                        'is_draft': False,
                        'is_solved': True,
                        'actual_start_date': datetime.now(),
                        'reason': 'Solved',
                    })

        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_operation.completion_issue_view_form').id,
            'target': 'new',
            'res_model': 'completion.issue.wizard',
            'res_id': self.completion_issue_wizard_id.id,
        }
