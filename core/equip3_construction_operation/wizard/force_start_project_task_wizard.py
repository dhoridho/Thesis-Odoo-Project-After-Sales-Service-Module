from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta


class ForceStartProjectTask(models.TransientModel):
    _name = 'force.start.project.task.const'
    _description = "Force Start Project Task"

    actual_start_date = fields.Date(string='Actual Start Date')
    project_task_id = fields.Many2one('project.task', string='project_task')
    warning = fields.Html(string='Warning', default= 'These tasks are in conflict. Please select the action you would like to take.' ,readonly=True)
    finish_to_start_issue_ids = fields.One2many('finish.to.start.task.issue', 'force_start_validation_id', string='Finish to Start Issue', readonly=True)
    def confirm(self):
        return self.project_task_id.write({'state': 'inprogress', 'purchase_order_exempt' : False, 'actual_start_date': self.actual_start_date})


class FinishToStartTaskIssue(models.TransientModel):
    _name = 'finish.to.start.task.issue'
    _description = 'Finish to Start Task Issue'

    project_task_id = fields.Many2one('project.task', string='Project Task')
    force_start_validation_id = fields.Many2one('force.start.project.task.const', string='Force Start Validation')
    parent_task_id = fields.Many2one('project.task', string='Job Order')
    # actual_start_date = fields.Datetime(string='Actual Start Date')
    # actual_end_date = fields.Datetime(string='Actual End Date')
    lag_qty = fields.Integer(string='Lag Qty')
    lag_type = fields.Selection([('day', 'Day'), ('hour', 'Hour')], string='Lag Type')
    reason = fields.Text(string='Reason')
