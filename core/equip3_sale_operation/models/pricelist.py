from odoo import models, fields, api, _

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    branch_id = fields.Many2one('res.branch','Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)