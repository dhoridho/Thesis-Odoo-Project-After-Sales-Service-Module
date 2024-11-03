from odoo import api, fields, models

class ProjectIssue(models.Model):
    _inherit = 'project.issue'
    _description = 'Project Issue Inherited'

    department_type = fields.Selection(related='project_id.department_type')
