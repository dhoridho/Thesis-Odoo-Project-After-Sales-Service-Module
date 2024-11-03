from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta


class FinishToFinishTaskValidationWizard(models.TransientModel):
    _name = 'finish.to.finish.task.validation.wizard'
    _description = 'Finish to Finish Task Validation Wizard'

    actual_end_date = fields.Datetime(string='Actual End Date')
    project_task_id = fields.Many2one('project.task', string='project_task')
    warning = fields.Html(string='Warning', default="These tasks are in conflict. Please select the action you would like to take.", readonly=True)
    predecessor_task_issue_ids = fields.One2many('finish.to.finish.predecessor.task.issue', 'finish_to_finish_task_validation_wizard_id',  
                                                string='Predecessor Task Issue')
    issue_solved = fields.Boolean(string='Issue Solved', default=False, 
        compute='_compute_issue_solved' )
    
    @api.depends('predecessor_task_issue_ids')
    def _compute_issue_solved(self):
        for record in self:
            check_issue = list()
            for issue in record.predecessor_task_issue_ids:
                check_issue.append(issue.is_solved)
            if False not in check_issue:
                record.issue_solved = True
            else:
                record.issue_solved = False

    def action_force_start_and_complete(self):
        for issue in self.predecessor_task_issue_ids:
            if issue.parent_task_id.state == 'draft':
                issue.write({'is_solved': True})
                issue.parent_task_id.write({'state': 'inprogress', 'progress_task': 100, 'purchase_order_exempt' : False})
            elif issue.parent_task_id.state == 'inprogress':
                issue.write({'is_solved': True})
                issue.parent_task_id.write({'state': 'inprogress', 'progress_task': 100, 'purchase_order_exempt' : False})

        return{             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.ff_validation_view_form').id,
                'target': 'new',
                'res_model': 'finish.to.finish.task.validation.wizard',
                'res_id': self.id,
        }

    def action_done(self):
        return self.project_task_id.write({'state': 'complete', 'actual_end_date': self.actual_end_date, 'purchase_order_exempt' : False})

    def action_cancel(self):
        return self.project_task_id.write({'state': 'inprogress', 'purchase_order_exempt' : False})


class PredecessorTaskIssue(models.TransientModel):
    _name = 'finish.to.finish.predecessor.task.issue'
    _description = 'Finish to Finish Predecessor Task Issue List'

    project_task_id = fields.Many2one('project.task', string='project_task')
    finish_to_finish_task_validation_wizard_id = fields.Many2one('finish.to.finish.task.validation.wizard', string='Finish to Finish Task Validation Wizard')
    parent_task_id = fields.Many2one('project.task', string='Job order')
    actual_start_date = fields.Datetime(string='Actual Start Date')
    actual_end_date = fields.Datetime(string='Actual End Date')
    lag_qty = fields.Integer(string='Lag Qty')
    lag_type = fields.Selection([('day', 'Day'), ('hour', 'Hour'), ('minute', 'Minute')], string='Lag Type')
    reason = fields.Text(string='Reason')
    is_draft = fields.Boolean(string='is_draft')
    is_solved = fields.Boolean(string='Is Solved', default=False)
    

    def button_force_complete(self):
        self.parent_task_id.write({'state': 'inprogress', 'progress_task': 100, 'purchase_order_exempt' : False})
        
        self.write({'is_solved': True})
        return{             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.ff_validation_view_form').id,
                'target': 'new',
                'res_model': 'finish.to.finish.task.validation.wizard',
                'res_id': self.finish_to_finish_task_validation_wizard_id.id,
        }


    def button_force_start(self):
        self.parent_task_id.write({'state': 'inprogress', 'purchase_order_exempt' : False, 'actual_start_date': datetime.now()})
        return{             
                'type': 'ir.actions.act_window',
                'view_mode': 'form', 
                'view_id': self.env.ref('equip3_construction_operation.ff_validation_view_form').id,
                'target': 'new',
                'res_model': 'finish.to.finish.task.validation.wizard',
                'res_id': self.finish_to_finish_task_validation_wizard_id.id,
        }

class FinishToFinishSuccessorValidation(models.Model):
    _name = 'finish.to.finish.successor.validation'
    _description = 'Finish to Finish Successor Validation'

    project_task_id = fields.Many2one('project.task', string='project_task')
    actual_end_date = fields.Datetime(string='Actual End Date')
    warning = fields.Html(string='Warning', default="These tasks are in conflict. Please select the action you would like to take.", readonly=True)
    successor_task_issue_ids = fields.One2many('finish.to.finish.successor.task.issue', 'finish_to_finish_successor_validation_id', string='Successor Task Issue')

    def button_force_complete(self):
        self.project_task_id.write({'state': 'complete', 'progress_task': 100, 'purchase_order_exempt' : False})

    def action_cancel(self):
        return self.project_task_id.write({'state': 'inprogress', 'purchase_order_exempt' : False})

class SuccessorTaskIssue(models.Model):
    _name = 'finish.to.finish.successor.task.issue'
    _description = 'Finish to Finish Successor Task Issue List'

    project_task_id = fields.Many2one('project.task', string='project_task')
    parent_task_id = fields.Many2one('project.task', string='project_task')
    finish_to_finish_successor_validation_id = fields.Many2one('finish.to.finish.successor.validation', string='Finish to Finish Successor Validation')
    lag_qty = fields.Integer(string='Lag Qty')
    lag_type = fields.Selection([('day', 'Day'), ('hour', 'Hour')], string='Lag Type')
    reason = fields.Text(string='Reason')

    




