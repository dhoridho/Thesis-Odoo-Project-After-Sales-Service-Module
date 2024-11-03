from odoo import _, api, fields, models

class InheritPurchaseRequestLineMakePuchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    def mod_make_purchase_order(self):
        res = super(InheritPurchaseRequestLineMakePuchaseOrder, self).mod_make_purchase_order()
        procurement_planning_id = self.pr_id.procurement_planning_id or False
        if procurement_planning_id:
            self.purchase_order_id.procurement_planning_id = procurement_planning_id
        return res