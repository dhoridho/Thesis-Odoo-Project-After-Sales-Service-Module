# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPaymentRegisterInv(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
    
    branch_id = fields.Many2one('res.branch', string='Branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
