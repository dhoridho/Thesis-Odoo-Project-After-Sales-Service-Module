from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class ApprovalMatrixPurchaseOrder(models.Model):
    _inherit = 'approval.matrix.purchase.order'

    project = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    
