from odoo import models, fields, api


def default_branch(self):
    if self.env.context.get('default_branch_id'):
        branch_id = self.env.context.get('default_branch_id')
    if self.env.user.branch_id:
        branch_id = self.env.user.branch_id.id
    if self.env.user.branch_ids:
        branch_id = self.env.user.branch_ids[0].id
    
    return False

def default_allowed_branch(self):
    user_branch = self.env.user.branch_id | self.env.user.branch_ids
    allowed_branch = user_branch.filtered(lambda b: b.company_id == self.company_id)

def compute_allowed_branch(self):
    user_branches = self.env.user.branch_id | self.env.user.branch_ids
    for record in self:
        allowed_branches = 


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    allowed_branch_ids = fields.Many2many(
        comodel_name='res.branch', 
        default=default_allowed_branch, 
        compute=compute_allowed_branch)

    branch_id = fields.Many2one(
        comodel_name='res.branch', 
        string='Branch', 
        default=default_branch, 
        domain="[('id', 'in', allowed_branch_ids)]")