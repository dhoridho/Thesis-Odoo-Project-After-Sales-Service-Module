from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpApprovalMatrixReject(models.TransientModel):
    _name = 'mrp.approval.matrix.reject'
    _description = 'MRP Approval Matrix Reject'

    @api.model
    def create(self, vals):
        res_model = vals.get('model_name', False)
        res_id = vals.get('model_id', False)
        try:
            if not self.env[res_model].browse(res_id).exists():
                raise ValidationError(_('Invalid Model ID!'))
        except KeyError:
            raise ValidationError(_('Invalid Model Name!'))
        return super(MrpApprovalMatrixReject, self).create(vals)

    model_name = fields.Char(required=True)
    model_id = fields.Integer(required=True)
    reason_id = fields.Many2one('mrp.approval.matrix.entry.reason', string='Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        record_id = self.env[self.model_name].browse(self.model_id)
        return record_id.with_context(skip_reject_wizard=True).action_reject(reason=self.reason_id)
