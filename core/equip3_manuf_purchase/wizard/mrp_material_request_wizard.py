from odoo import models, fields, api, _


class MRPMaterialRequestWizard(models.TransientModel):
    _inherit = 'mrp.material.request.wizard'

    action = fields.Selection(selection_add=[
        ('action_purchase_request', 'Create Purchase Request'),
    ], ondelete={'action_purchase_request': 'cascade'})

    def _allowed_orders(self):
        if self.action == 'action_purchase_request':
            return self.plan_id.mrp_order_ids.filtered(lambda o: not o.is_purchase_requested)
        return super(MRPMaterialRequestWizard, self)._allowed_orders()
