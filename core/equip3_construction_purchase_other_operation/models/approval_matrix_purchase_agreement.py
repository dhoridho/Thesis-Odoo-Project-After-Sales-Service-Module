from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class ApprovalMatrixPurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement.approval.matrix'

    project = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    
