from odoo import fields, models, api, _


class AssignPRWizard(models.TransientModel):
    _name = 'assign.pr.wizard'
    _description = 'Assign PR Wizard'

    pr_ids = fields.Many2many(comodel_name='purchase.request.line', string='PR Lines active')
    line_ids = fields.One2many(comodel_name='assign.pr.line.wizard', inverse_name='wizard_id', string='Lines')
    @api.onchange('pr_ids')
    def _onchange_pr_ids(self):
        if self.pr_ids:
            line_ids = []
            for pr in self.pr_ids:
                vals = {
                    'pr_line_id':pr._origin.id,
                    'name':pr.request_id.name,
                    'user_id':pr._origin.assigned_to.id,
                    'product_id':pr.product_id.id,
                }
                line_ids.append((0,0,vals))
            if line_ids:
                self.line_ids = line_ids

    def action_submit(self):
        for line in self.line_ids:
            line.pr_line_id.assigned_to = line.new_user_id
        

class AssignPRLineWizard(models.TransientModel):
    _name = 'assign.pr.line.wizard'
    _description = 'Assign PR Line Wizard'

    wizard_id = fields.Many2one(comodel_name='assign.pr.wizard', string='Wizard')
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
    
    
    

    