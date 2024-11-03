from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date, timedelta


class ProjectTaskCompletionWizard(models.TransientModel):
    """Project task completion validation will be handled here"""
    _name = 'project.task.completion.wizard'
    _description = "Project Task Completion Wizard"

    actual_end_date = fields.Datetime(string='Actual End Date', required=True)
    project_task_id = fields.Many2one('project.task', string='project_task')
    reason = fields.Text(string="Reason")

    def confirm(self):
        predecessor_conflict = list()
        predecessor_data = {}

        if len(self.project_task_id.predecessor_ids)>0:
            for record in self.project_task_id.predecessor_ids:
                # Finish to Finish conflict check
                if record.type  == 'FF':
                    if record.parent_task_id.state == 'draft':
                        predecessor_conflict.append(record.parent_task_id.id)
                        predecessor_data[record.parent_task_id.id] = {
                            'actual_start_date': False, 
                            'is_draft': True, 
                            'is_time_conflict': False,
                            'type': 'FF',  
                            'lag_qty': record.lag_qty, 
                            'lag_type': record.lag_type, 
                            'reason': 'Predecessor task is in draft state'}
                    elif record.parent_task_id.state == 'inprogress':
                        if record.parent_task_id.progress_task <100:
                            predecessor_conflict.append(record.parent_task_id.id)
                            predecessor_data[record.parent_task_id.id] = {
                                'actual_start_date': record.parent_task_id.actual_start_date, 
                                'is_draft': False, 
                                'is_time_conflict': False, 
                                'type': 'FF', 
                                'lag_qty': record.lag_qty, 
                                'lag_type': record.lag_type, 
                                'reason': 'Predecessor task progress is %s' % (record.parent_task_id.progress_task)+'%'}
                    elif record.parent_task_id.state == 'complete':
                        if record.parent_task_id.actual_end_date:
                            actual_end_date = False
                            if record.lag_type == 'day':
                                actual_end_date = record.parent_task_id.actual_end_date + timedelta(days=record.lag_qty)
                            elif record.lag_type == 'hour':
                                actual_end_date = record.parent_task_id.actual_end_date + timedelta(hours=record.lag_qty)
                            elif record.lag_type == 'minute':
                                actual_end_date = record.parent_task_id.actual_end_date + timedelta(minutes=record.lag_qty)

                            if self.actual_end_date < actual_end_date:
                                predecessor_conflict.append(record.parent_task_id.id)
                                predecessor_data[record.parent_task_id.id] = {
                                    'actual_start_date': record.parent_task_id.actual_start_date, 
                                    'is_draft': False, 
                                    'is_time_conflict': True,
                                    'type': 'FF', 
                                    'lag_qty': record.lag_qty, 
                                    'lag_type': record.lag_type, 
                                    'reason': 'Predecessor actual end date conflicted with task\'s time lag'}
                elif record.type == 'SF':
                    if record.parent_task_id.state == 'draft':
                        predecessor_conflict.append(record.parent_task_id.id)
                        predecessor_data[record.parent_task_id.id] = {
                            'actual_start_date': False, 
                            'is_draft': True, 
                            'is_time_conflict': False,
                            'type': 'SF', 
                            'lag_qty': record.lag_qty, 
                            'lag_type': record.lag_type, 
                            'reason': 'Predecessor task is in draft state'}
                    elif record.parent_task_id.state == 'inprogress':
                        if record.parent_task_id.actual_start_date:
                            lag_start_date = False
                            if record.lag_type == 'day':
                                lag_start_date = record.parent_task_id.actual_start_date + timedelta(days=record.lag_qty)
                            elif record.lag_type == 'hour':
                                lag_start_date = record.parent_task_id.actual_start_date + timedelta(hours=record.lag_qty)
                            elif record.lag_type == 'minute':
                                lag_start_date = record.parent_task_id.actual_start_date + timedelta(minutes=record.lag_qty)

                            if self.actual_end_date < lag_start_date:
                                predecessor_conflict.append(record.parent_task_id.id)
                                predecessor_data[record.parent_task_id.id] = {
                                    'actual_start_date': record.parent_task_id.actual_start_date, 
                                    'is_draft': False, 
                                    'is_time_conflict': True,
                                    'type': 'SF', 
                                    'lag_qty': record.lag_qty, 
                                    'lag_type': record.lag_type, 
                                    'reason': 'Task\'s actual end date conflicted with predecessor\'s time lag'}

        # If conflict exist then direct to completion issue wizard
        if len(predecessor_conflict) > 0:
            completion_issue = self.env['completion.issue.wizard'].create({
                'actual_end_date': self.actual_end_date,
                'project_task_id': self.project_task_id.id,
            })
            for i in range(len(predecessor_conflict)):
                completion_issue.issue_ids.create({
                    'completion_issue_wizard_id': completion_issue.id,
                    'parent_task_id': predecessor_conflict[i],
                    'type': predecessor_data[predecessor_conflict[i]]['type'],
                    'actual_start_date': predecessor_data[predecessor_conflict[i]]['actual_start_date'] or False,
                    'actual_end_date': False,
                    'is_time_conflict': predecessor_data[predecessor_conflict[i]]['is_time_conflict'] or False,
                    'is_draft': predecessor_data[predecessor_conflict[i]]['is_draft'],
                    'lag_qty': predecessor_data[predecessor_conflict[i]]['lag_qty'],
                    'lag_type': predecessor_data[predecessor_conflict[i]]['lag_type'],
                    'reason': predecessor_data[predecessor_conflict[i]]['reason'],
                })
            return{
                'name': _('Confirmation'),             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.completion_issue_view_form').id,
                'target': 'new',
                'res_model': 'completion.issue.wizard',
                'res_id': completion_issue.id,
                }

        else:
            self.project_task_id.write({'state': 'complete',
                                        'reason_status' : self.reason,
                                        'progress_task': 100, 
                                        'actual_end_date': self.actual_end_date})


    def action_cancel(self):
        self.project_task_id.write({'state': 'inprogress'})

