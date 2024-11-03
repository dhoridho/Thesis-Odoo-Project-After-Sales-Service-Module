from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SplitPRWizard(models.TransientModel):
    _name = 'split.pr.wizard'
    _description = 'Assign PR Wizard'

    pr_line_id = fields.Many2one(comodel_name='purchase.request.line', string='Purchase Request Line')
    product_qty = fields.Float(string='Qty')
    
    line_ids = fields.One2many(comodel_name='split.pr.line.wizard', inverse_name='wizard_id', string='Lines')
    @api.onchange('pr_line_id')
    def _onchange_pr_line_id(self):
        if self.pr_line_id:
            self.product_qty = self.pr_line_id.product_qty
            line_ids = []
            vals = {
                'pr_line_id':self.pr_line_id._origin.id,
                'name':self.pr_line_id.request_id.name,
                'user_id':self.pr_line_id._origin.assigned_to.id,
                'new_user_id':self.pr_line_id._origin.assigned_to.id,
                'product_id':self.pr_line_id.product_id.id,
                'product_qty':self.pr_line_id.product_qty,
            }
            line_ids.append((0,0,vals))
            self.line_ids = line_ids

    def action_submit(self):
        product_qty = self.product_qty
        new_product_qty = sum(self.line_ids.mapped('product_qty'))
        if product_qty != new_product_qty:
            raise ValidationError(_("Total Qty tidak sama dengan sebelumnya"))
        for line in self.line_ids:
            if line.product_qty > 0:
                if line.pr_line_id:
                    line.pr_line_id.product_qty = line.product_qty
                    if line.pr_line_id.assigned_to != line.new_user_id:
                        line.pr_line_id.assigned_to = line.new_user_id.id
                else:
                    new_pr_line = self.pr_line_id.copy()
                    new_pr_line.product_qty = line.product_qty
                    new_pr_line.dest_loc_id = self.pr_line_id.dest_loc_id.id
                    new_pr_line.date_required = self.pr_line_id.date_required
                    if new_pr_line.assigned_to != line.new_user_id:
                        new_pr_line.assigned_to = line.new_user_id.id
        

class SplitPRLineWizard(models.TransientModel):
    _name = 'split.pr.line.wizard'
    _description = 'Assign PR Line Wizard'

    wizard_id = fields.Many2one(comodel_name='split.pr.wizard', string='Wizard')
    pr_line_id = fields.Many2one(comodel_name='purchase.request.line', string='Purchase Request')
    name = fields.Char(string='Reference', readonly=True)
    user_id = fields.Many2one(comodel_name='res.users', string='Purchase Representative', readonly=True)
    new_user_id = fields.Many2one(comodel_name='res.users', string='New Purchase Representative', readonly=False, 
        domain=lambda self: [
            (
                "groups_id",
                "in",
                [self.env.ref("purchase_request.group_purchase_request_user").id,self.env.ref("purchase_request.group_purchase_request_manager").id],
            )
        ],)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', readonly=True)
    product_qty = fields.Float(string='Product Qty')
    
    @api.onchange('pr_line_id')
    def _onchange_pr_line_id(self):
        if self.pr_line_id:
            pr_line_id = self.pr_line_id
            self.pr_line_id = False
            self.name=pr_line_id.request_id.name
            self.user_id=pr_line_id._origin.assigned_to.id
            self.new_user_id=pr_line_id._origin.assigned_to.id
            self.product_id=pr_line_id.product_id.id
            self.product_qty=0
    
    
    

    