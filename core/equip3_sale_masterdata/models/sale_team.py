from odoo import models,fields


class SaleTeamInherit(models.Model):
    _inherit = 'crm.team'

    def _domain_user_id(self):
        current_company_id = self.env.company.id
        available_users=self.env['res.users'].search([('share', '=', False)]).filtered(lambda u,current_company_id=current_company_id:current_company_id in u.company_ids.ids)
        return [('id','in',available_users.ids)]

    user_id = fields.Many2one('res.users', string='Team Leader', check_company=True, domain=_domain_user_id)
