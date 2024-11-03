from odoo import api, fields, models, _


class ResBranch(models.Model):
    _inherit = 'res.branch'

    @api.model
    def create(self, values):
        res = super().create(values)
        users = self.env['res.users'].sudo().search([('is_tendor_vendor', '=', True),('company_id', '=', self.env.company.id)])
        for user in users:
            user.write({
                'branch_ids': [(4, res.id)]
            })
        return res