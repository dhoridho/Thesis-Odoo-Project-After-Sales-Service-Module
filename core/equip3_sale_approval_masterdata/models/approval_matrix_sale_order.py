from odoo import models,fields,api


class salesOrderMatrix(models.Model):
    _inherit = "approval.matrix.sale.order.lines"
    
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")
    
    @api.onchange('approver_types')
    def _onchange_approver_types(self):
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_name_ids:
                data.user_name_ids = False
                
    def write(self, vals):
        res =  super(salesOrderMatrix,self).write(vals)
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_name_ids and not data.order_id:
                data.user_name_ids = False
        return res