from odoo import fields, models, _


class InternalApprovalMatrixLine(models.Model):
    _inherit = "itr.approval.matrix.line"

    transfer_id = fields.Many2one(
        'internal.transfer', string="Approval Matrix")
