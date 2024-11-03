from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class ApprovalMatrixBlanketOrder(models.Model):
    _inherit = 'approval.matrix.blanket.order'

    project = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    
