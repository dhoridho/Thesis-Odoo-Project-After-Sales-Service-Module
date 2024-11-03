
from odoo import _, api, fields, models


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        if context.get('active_model') == 'purchase.request':
            purchase_request_ids = self.env['purchase.request'].browse(context.get("active_ids"))
            res['analytic_account_group_ids'] = [(6, 0, purchase_request_ids.analytic_account_group_ids.ids)]
        elif context.get('active_model') == 'purchase.request.line':
            purchase_request_line_ids = self.env['purchase.request.line'].browse(context.get("active_ids"))
            res['analytic_account_group_ids'] = [(6, 0, purchase_request_line_ids.mapped('request_id.analytic_account_group_ids').ids)]
        return res
