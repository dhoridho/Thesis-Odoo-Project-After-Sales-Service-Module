from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class ApprovalMatrixPurchaseRequest(models.Model):
    _inherit = 'approval.matrix.purchase.request'

    project = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    
