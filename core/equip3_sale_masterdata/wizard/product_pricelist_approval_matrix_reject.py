from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductPricelistApprovalMatrixReject(models.TransientModel):
    _name = 'product.pricelist.approval.matrix.reject'
    _description = 'Product Pricelist Approval Matrix Reject'

    pricelist_request_id = fields.Many2one('product.pricelist.request', required=True)
    reason = fields.Text(string='Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        return self.pricelist_request_id.with_context(skip_reject_wizard=True).action_reject(reason=self.reason)
