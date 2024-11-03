from odoo import models,fields


class DevPurchaseTeamInherit(models.Model):
    _inherit = 'dev.purchase.team'

    company_id = fields.Many2one('res.company', default=lambda self:self.env.user.company_id, required="1", readonly=True)
    branch_id = fields.Many2one('res.branch', "Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])