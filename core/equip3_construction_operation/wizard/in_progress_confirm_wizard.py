from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta


class InProgressConfirm(models.TransientModel):
    _name = 'in.progress.confirm.const'
    _description = "Project Task In Progress Confirmation"

    actual_start_date = fields.Datetime(string='Actual Start Date', required=True)
    project_id = fields.Many2one('project.project', string='Project')
    project_task_id = fields.Many2one('project.task', string='Job Order')

    @api.onchange('actual_start_date')
    def _onchange_actual_start_date(self):
        if self.project_task_id.is_subtask:
            if self.actual_start_date:
                if self.actual_start_date <= self.project_task_id.planned_start_date:
                    raise ValidationError(_('Actual Start Date cannot be less than Planned Start Date.'))
                elif self.actual_start_date >= self.project_task_id.planned_end_date:
                    raise ValidationError(_('Actual Start Date cannot be greater than Planned End Date.'))

    def confirm(self):
        predecessor_conflict = list()
        predecessor_data = {}
        labour_usages = []
        if len(self.project_task_id.predecessor_ids) > 0:
            for record in self.project_task_id.predecessor_ids:
                # Finish to start conflict check
                if record.type == 'FS':
                    lag_end_date = False
                    if record.parent_task_id.actual_end_date:
                        if record.lag_type == 'day':
                            lag_end_date = record.parent_task_id.actual_end_date + timedelta(days=record.lag_qty)
                        elif record.lag_type == 'minute':
                            lag_end_date = record.parent_task_id.actual_end_date + timedelta(minutes=record.lag_qty)
                        elif record.lag_type == 'hour':
                            lag_end_date = record.parent_task_id.actual_end_date + timedelta(hours=record.lag_qty)

                    if record.parent_task_id.state == 'draft':
                        predecessor_conflict.append(record.parent_task_id.id)
                        predecessor_data[record.parent_task_id.id] = {
                            'actual_start_date': False,
                            'is_draft': True,
                            'is_solved': False,
                            'is_time_conflict': False,
                            'type': 'FS',
                            'lag_qty': record.lag_qty,
                            'lag_type': record.lag_type,
                            'reason': 'Incomplete predecessor task'
                        }
                    elif record.parent_task_id.state == 'inprogress':
                        predecessor_conflict.append(record.parent_task_id.id)
                        predecessor_data[record.parent_task_id.id] = {
                            'actual_start_date': record.parent_task_id.actual_start_date or False,
                            'is_draft': False,
                            'is_solved': False,
                            'is_time_conflict': False,
                            'type': 'FS',
                            'lag_qty': record.lag_qty,
                            'lag_type': record.lag_type,
                            'reason': 'Incomplete predecessor task'
                        }
                    elif record.parent_task_id.state == 'complete':
                        if self.actual_start_date <= lag_end_date:
                            predecessor_conflict.append(record.parent_task_id.id)
                            predecessor_data[record.parent_task_id.id] = {
                                'actual_start_date': record.parent_task_id.actual_start_date or False,
                                'is_draft': False,
                                'is_solved': False,
                                'is_time_conflict': True,
                                'type': 'FS',
                                'lag_qty': record.lag_qty,
                                'lag_type': record.lag_type,
                                'reason': 'Actual start date conflicted with predecessor\'s time lag'
                            }

                # Start to start conflict check
                elif record.type == 'SS':
                    lag_start_date = False
                    if record.parent_task_id.actual_start_date:
                        if record.lag_type == 'day':
                            lag_start_date = record.parent_task_id.actual_start_date + timedelta(days=record.lag_qty)
                        elif record.lag_type == 'minute':
                            lag_start_date = record.parent_task_id.actual_start_date + timedelta(minutes=record.lag_qty)
                        elif record.lag_type == 'hour':
                            lag_start_date = record.parent_task_id.actual_start_date + timedelta(hours=record.lag_qty)

                    if record.parent_task_id.state == 'draft':
                        predecessor_conflict.append(record.parent_task_id.id)
                        predecessor_data[record.parent_task_id.id] = {
                            'actual_start_date': False,
                            'is_draft': True,
                            'is_time_conflict': False,
                            'type': 'SS',
                            'lag_qty': record.lag_qty,
                            'lag_type': record.lag_type,
                            'reason': 'Predecessor task is in draft state'}
                    elif record.parent_task_id.state == 'inprogress':
                        if self.actual_start_date <= lag_start_date:
                            predecessor_conflict.append(record.parent_task_id.id)
                            predecessor_data[record.parent_task_id.id] = {
                                'actual_start_date': record.parent_task_id.actual_start_date or False,
                                'is_draft': False,
                                'is_time_conflict': True,
                                'type': 'SS',
                                'lag_qty': record.lag_qty,
                                'lag_type': record.lag_type,
                                'reason': 'Actual start date conflicted with predecessor\'s time lag'
                            }
        # If conflict exist then direct to inprogress issue wizard            
        if len(predecessor_conflict) > 0:
            inprogress_issue = self.env['inprogress.issue.wizard'].create(
                {'actual_start_date': self.actual_start_date, 'project_task_id': self.project_task_id.id})

            for i in range(len(predecessor_conflict)):
                inprogress_issue.inprogress_issue_ids.create(
                    {'project_task_id': self.project_task_id.id,
                     'inprogress_validation_id': inprogress_issue.id,
                     'parent_task_id': predecessor_conflict[i],
                     'actual_start_date': predecessor_data[predecessor_conflict[i]]['actual_start_date'],
                     'is_time_conflict': predecessor_data[predecessor_conflict[i]]['is_time_conflict'],
                     'is_draft': predecessor_data[predecessor_conflict[i]]['is_draft'],
                     'type': predecessor_data[predecessor_conflict[i]]['type'],
                     'lag_qty': predecessor_data[predecessor_conflict[i]]['lag_qty'],
                     'lag_type': predecessor_data[predecessor_conflict[i]]['lag_type'],
                     'reason': predecessor_data[predecessor_conflict[i]]['reason'],
                     })
            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirmation'),
                'view_mode': 'form',
                'target': 'new',
                'res_model': 'inprogress.issue.wizard',
                'res_id': inprogress_issue.id,
            }
        else:
            self.project_task_id.write(
                {'state': 'inprogress', 'purchase_order_exempt': False, 'actual_start_date': self.actual_start_date})
            if not self.project_id.act_start_date:
                self.project_id.write({'act_start_date': self.actual_start_date.date()})
            if not self.project_task_id.is_subtask:
                cost_sheet = False
                project_budget = False
                for labour in self.project_task_id.labour_usage_ids:
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

