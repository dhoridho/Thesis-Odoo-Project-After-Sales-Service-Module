from odoo import api, fields, models, _


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    user_id = fields.Many2one('res.users',
                              'User',
                              default=lambda self: self.env.user)
    # branch_id = fields.Many2one('res.branch',
    #                             related='user_id.branch_id',
    #                             readonly=False, domain="[('company_id', '=', company_id)]")

    @api.onchange('date', 'category_id', 'date_first_depreciation')
    def branch_domain(self):
        res = {}
        if self.user_id and self.user_id.branch_ids:
            res = {
                'domain': {
                    'branch_id': [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
                }
            }
        return res
    
    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        return
    
class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id.id)
