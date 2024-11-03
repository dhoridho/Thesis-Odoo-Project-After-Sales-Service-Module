from odoo import models,fields,api


class stockInventroyMatrix(models.Model):
    _inherit = "stock.inventory.approval.matrix.line"
    
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")
    
    @api.onchange('approver_types')
    def _onchange_approver_types(self):
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_ids:
                data.user_ids = False
                
    def write(self, vals):
        res =  super(stockInventroyMatrix,self).write(vals)
        for data in self:
            if data.approver_types == 'by_hierarchy' and data.user_ids and not data.st_inv_id:
                data.user_ids = False
        return res