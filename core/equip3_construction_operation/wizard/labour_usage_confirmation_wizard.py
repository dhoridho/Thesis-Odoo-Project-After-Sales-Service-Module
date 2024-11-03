from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class LabourUsageConfirmationWizard(models.TransientModel):
    _name = 'labour.usage.confirmation.wizard'
    _description = 'Labour Usage Confirmation'

    warning_text = fields.Text(string='Warning', readonly=True, default="Labour data on this Job Order is empty. You cannot add labour data once the Job Order is already In Progress. Continue?")
    project_task_id = fields.Many2one('project.task', string='Job Order')

    def confirm(self):
        return self.project_task_id.action_inprogress(True)
