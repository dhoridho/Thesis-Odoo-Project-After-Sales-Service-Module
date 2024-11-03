from odoo import fields, models

class Lead(models.Model):
    _inherit = 'crm.lead'

    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])