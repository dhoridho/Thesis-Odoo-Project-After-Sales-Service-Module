from odoo import _, api, fields, models


# from odoo.exceptions import ValidationError, UserError


class ProjectCancelResponsible(models.TransientModel):
    _name = 'project.cancel.responsible'
    _description = 'Project Cancel Responsible'

    responsible = fields.Selection([('contractor', 'Contractor'), ('client', 'Client')], string='Responsible',
                                   required=True)
    reason = fields.Text(string='Reason', required=True)
    project_id = fields.Many2one('project.project', string='Project')

    def responsible_confirm(self):
        if self.project_id:
            self.project_id.responsible = self.responsible
            self.project_id.primary_states = 'cancelled'
