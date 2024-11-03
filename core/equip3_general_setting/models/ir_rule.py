from odoo import models, api


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain_keys(self):
        return super(IrRule, self)._compute_domain_keys() + ['allowed_branch_ids']

    @api.model
    def _eval_context(self):
        context = super(IrRule, self)._eval_context()
        context.update({
            'branch_id': self.env.branch.id,
            'branch_ids': self.env.branches.ids
        })
        return context
