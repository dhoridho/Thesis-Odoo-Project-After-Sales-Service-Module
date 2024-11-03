from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta


class InProgressIssueWizard(models.TransientModel):
    """Project task inprogress validation will be handled here"""
    _name = 'inprogress.issue.wizard'
    _description = 'In Progress Issue Wizard'

    actual_start_date = fields.Datetime(string='Actual Start Date')
    project_task_id = fields.Many2one('project.task', string='project_task')
    warning = fields.Html(string='Warning', default= 'These tasks are in conflict. Please select the action you would like to take.' ,readonly=True)
    warning_bottom = fields.Html(string='Warning', default= 'If you would like to force current task only, please click this button.' ,readonly=True)
    inprogress_issue_ids = fields.One2many('inprogress.issue', 'inprogress_validation_id', string='Issue', readonly=True)
    is_issues_solved = fields.Boolean(string='Issues Solved', default=False, compute='_compute_issues_solved')

    @api.depends('inprogress_issue_ids')
    def _compute_issues_solved(self):
        for record in self:
            check_issue = list()
            for issue in record.inprogress_issue_ids:
                check_issue.append(issue.is_solved)
            if False not in check_issue:
                record.is_issues_solved = True
            else:
                record.is_issues_solved = False

    def check_all_time_conflict(self):
        for issue in self.inprogress_issue_ids:
            if issue.is_time_conflict is False:
                return False
        return True

    def force_confirm(self, task=False):
        labour_usages = []
        task.write({
            'state': 'inprogress',
            'purchase_order_exempt': False,
            'actual_start_date': self.actual_start_date
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

    def force_complete(self, task):
        task.write({
            'state': 'complete',
            'progress_task': 100,
            'actual_end_date': datetime.now()
        })
        return True

    def action_force_start_and_complete(self):
        # Force all action available in list to be executed
        if self.check_all_time_conflict():
            # If all issue left are time conflict, then start the task
            return self.force_confirm(self.project_task_id)
        else:
            for issue in self.inprogress_issue_ids:
                if issue.parent_task_id.state == 'draft':
                    self.force_confirm(issue.parent_task_id)

                    if issue.type == 'FS':
                        issue.write({
                            'is_draft': False,
                            'actual_start_date': datetime.now(),
                            'reason': 'Predecessor task progress is %s' % (issue.parent_task_id.progress_task)+'%',
                        })

                    elif issue.type == 'SS':
                        if issue.parent_task_id.actual_start_date:
                            if issue.lag_type == 'day':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(days=issue.lag_qty)
                            elif issue.lag_type == 'hour':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(hours=issue.lag_qty)
                            elif issue.lag_type == 'minute':
                                lag_start_date = issue.parent_task_id.actual_start_date + timedelta(minutes=issue.lag_qty)

                            if issue.parent_task_id.actual_start_date <= lag_start_date:
                                issue.write({
                                    'is_draft': False,
                                    'actual_start_date': datetime.now(),
                                    'is_time_conflict': True,
                                    'reason': 'Actual start date conflicted with predecessor\'s time lag'
                                })
                            else:
                                issue.write({
                                    'is_draft': False,
                                    'actual_start_date': datetime.now(),
                                    'is_solved': True,
                                    'reason': 'Solved'
                                })

                elif issue.parent_task_id.state == 'inprogress':
                    if issue.type == 'FS':
                        # issue.parent_task_id.write({
                        #     'state': 'complete',
                        #     'progress_task': 100,
                        #     'actual_end_date': datetime.now()
                        #     })
                        self.force_complete(issue.parent_task_id)
                        if issue.parent_task_id.actual_end_date:
                            lag_end_date = False
                            if issue.lag_type == 'day':
                                lag_end_date = issue.parent_task_id.actual_end_date + timedelta(days=issue.lag_qty)
                            elif issue.lag_type == 'hour':
                                lag_end_date = issue.parent_task_id.actual_end_date + timedelta(hours=issue.lag_qty)
                            elif issue.lag_type == 'minute':
                                lag_end_date = issue.parent_task_id.actual_end_date + timedelta(minutes=issue.lag_qty)

                        
                            if issue.inprogress_validation_id.actual_start_date <= lag_end_date:
                                issue.write({'is_solved': True,
                                            'is_time_conflict': True,
                                            'actual_end_date': datetime.now(),
                                            'reason': 'Actual start date conflicted with predecessor\'s time lag'})
                            else:
                                issue.write({'is_solved': True,
                                            'actual_end_date': datetime.now(),
                                            'reason': 'Solved'})

            # If all issues are solved, then start current task
            if self.is_issues_solved:
                return self.force_confirm(self.project_task_id)
            else:
                return{
                        'name': _('Confirmation'),             
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form', 
                        'view_id': self.env.ref('equip3_construction_operation.inprogress_issue_wizard_wizard_view_form').id,
                        'target': 'new',
                        'res_model': 'inprogress.issue.wizard',
                        'res_id': self.id,
                }

    def action_force_start_current(self):
        return self.force_confirm(self.project_task_id)


class InProgressIssues(models.TransientModel):
    '''List of inprogress issues'''
    _name = 'inprogress.issue'
    _description = 'In Progress Issues'

    project_task_id = fields.Many2one('project.task', string='Project Task')
    inprogress_validation_id = fields.Many2one('inprogress.issue.wizard', string='Force Start Validation')
    parent_task_id = fields.Many2one('project.task', string='Job Order')
    actual_start_date = fields.Datetime(string='Actual Start Date')
    actual_end_date = fields.Datetime(string='Actual End Date')
    type = fields.Selection([('FS', 'Finish to Start'), ('FF', 'Finish to Finish'), ('SS', 'Start to Start')], string='Type')
    lag_qty = fields.Integer(string='Lag Qty')
    lag_type = fields.Selection([('day', 'Day'), ('hour', 'Hour'), ('minute', 'Minute')], string='Lag Type')
    reason = fields.Text(string='Reason')
    is_draft = fields.Boolean(string='Is Draft', default=False)
    is_time_conflict = fields.Boolean(string='Is Time Conflict', default=False)
    is_solved = fields.Boolean(string='Is Solved', default=False)

    def action_force_start(self):
        # self.parent_task_id.write({
        #         'state': 'inprogress',
        #         'purchase_order_exempt' : False,
        #         'actual_start_date': datetime.now(),
        #         })
        self.inprogress_validation_id.force_confirm(self.parent_task_id)
        if self.type == 'FS':
            self.write({
                'is_draft': False,
                'actual_start_date': datetime.now(),
                'reason': 'Predecessor task progress is %s' % (self.parent_task_id.progress_task)+'%',
            })
        elif self.type == 'SS':
            if self.parent_task_id.actual_start_date:
                if self.lag_type == 'day':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(days=self.lag_qty)
                elif self.lag_type == 'hour':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(hours=self.lag_qty)
                elif self.lag_type == 'minute':
                    lag_start_date = self.parent_task_id.actual_start_date + timedelta(minutes=self.lag_qty)

                if self.parent_task_id.actual_start_date <= lag_start_date:
                    self.write({
                        'is_draft': False,
                        'actual_start_date': datetime.now(),
                        'is_time_conflict': True,
                        'reason': 'Actual start date conflicted with predecessor\'s time lag'
                    })
                else:
                    self.write({
                        'is_draft': False,
                        'actual_start_date': datetime.now(),
                        'is_solved': True,
                        'is_time_conflict': False,
                        'reason': 'Solved'
                    })

        return{
                'name': _('Confirmation'),             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.inprogress_issue_wizard_wizard_view_form').id,
                'target': 'new',
                'res_model': 'inprogress.issue.wizard',
                'res_id': self.inprogress_validation_id.id,
        }

    def action_force_complete(self):
        if self.type == 'FS':
            # self.parent_task_id.write({
            #     'state': 'complete',
            #     'progress_task': 100,
            #     'actual_end_date': datetime.now()
            #     })
            self.inprogress_validation_id.force_complete(self.parent_task_id)
            if self.parent_task_id.actual_end_date:
                lag_end_date = False
                if self.lag_type == 'day':
                    lag_end_date = self.parent_task_id.actual_end_date + timedelta(days=self.lag_qty)
                elif self.lag_type == 'hour':
                    lag_end_date = self.parent_task_id.actual_end_date + timedelta(hours=self.lag_qty)
                elif self.lag_type == 'minute':
                    lag_end_date = self.parent_task_id.actual_end_date + timedelta(minutes=self.lag_qty)

            
                if self.inprogress_validation_id.actual_start_date <= lag_end_date:
                    self.write({'is_solved': True,
                                'actual_end_date': datetime.now(),
                                'is_time_conflict': True,
                                'reason': 'Actual start date conflicted with predecessor\'s time lag'})
                else:
                    self.write({'is_solved': True,
                                'actual_end_date': datetime.now(),
                                'is_time_conflict': False,
                                'reason': 'Solved'})

        return{
                'name': _('Confirmation'),             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.inprogress_issue_wizard_wizard_view_form').id,
                'target': 'new',
                'res_model': 'inprogress.issue.wizard',
                'res_id': self.inprogress_validation_id.id,
        }

    
