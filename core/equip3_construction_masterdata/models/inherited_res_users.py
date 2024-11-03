# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = 'res.users'


    project_ids = fields.Many2many(relation='project_associated_rel', comodel_name='project.project',
                                        column1='associated_id', column2='project_id',string="Allowed Projects")
    department_id = fields.Many2one('hr.department', string="Department")
