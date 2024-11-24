from odoo import api, fields, models, _


class MaterialApprovalMatrixLine(models.Model):
    _inherit = "mr.approval.matrix.line"

    mr_matrix_id = fields.Many2one(
        'material.request', string="Approval Matrix")
