from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountAnalyticTag(models.Model):
    _name = 'account.analytic.tag'
    _inherit = ['account.analytic.tag','mail.thread','mail.activity.mixin']
    _description = 'Account Analytic Tag'

    

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id', '=', self.env.company.id)]

    name = fields.Char(string='Analytic Group', index=True, required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one('res.branch', string="Branch", domain=_domain_branch)

    



    @api.onchange('company_id')
    def _get_domain(self):
        return {'domain':{'branch_id':f"[('id','in',{[x.id for x in self.env.user.branch_ids]})]"}}

    @api.model
    def default_get(self, fields):
        vals = super(AccountAnalyticTag, self).default_get(fields)
        vals['active_analytic_distribution'] = True
        return vals

    @api.onchange('branch_id')
    @api.depends('branch_id')
    def _onchange_branch_id(self):
        self.company_id = self.env.company
        

class ResUsers(models.Model):
    _inherit = 'res.users'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', relation='users_analytic_tag_rel', string='Analytic Group')
    allow_analytic_group = fields.Boolean('Allow Create/Edit Analytic Group')


class BranchAccountAnalyticTag(models.Model):
    _inherit = 'res.branch'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', relation='branch_analytic_tag_rel', string='Analytic Group')


class ProductCategoryAnalyticTag(models.Model):
    _inherit = 'product.category'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', relation='product_category_analytic_tag_rel', string='Analytic Group')

class AccountAnalyticPriority(models.Model):
    _name = 'analytic.priority'
    _description = 'Account Priority'
    _order = "priority"
    
    priority = fields.Integer('Priority')
    object_id = fields.Selection([
        ('user', 'User'), 
        ('branch', 'Branch'),
        ('product_category', 'Product Category')
        ])