from odoo import models,fields,api


class ApprovalMatrixPurchaseOrder(models.Model):
    _inherit = "approval.matrix.purchase.order.line"
    
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")
    
    @api.onchange('approver_types')
    def _onchange_approver_types(self):
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_ids:
                data.user_ids = False
                
    def write(self, vals):
        res =  super(ApprovalMatrixPurchaseOrder,self).write(vals)
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_ids and not data.order_id:
                data.user_ids = False
        return res