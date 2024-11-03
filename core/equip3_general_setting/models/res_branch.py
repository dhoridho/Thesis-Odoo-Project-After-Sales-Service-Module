from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class ResBranch(models.Model):
    _inherit = 'res.branch'

    def unlink(self):
        users = self.env['res.users'].sudo().search([])
        for branch in self:
            """ Let res.users handle the constraints """
            branch_users = users.filtered(lambda u: branch in u.branch_ids)
            if branch_users:
                user_names = '\n'.join(['- %s' % user.name for user in branch_users])
                raise ValidationError(_('Branch %s used as default branch(s) for user:\n%s\n\nPlease remove them first!' % (branch.name, user_names)))
        return super(ResBranch, self).unlink()

    @api.constrains('name', 'company_id')
    def _constrains_name_company(self):
        """ much simpler with _sql_constraints, 
        but we need showing branch name in the error message """
        for branch in self:
            company = branch.company_id
            if not company:
                continue
            branch_name = branch.name
            if company.branch_ids.filtered(lambda b: b.name == branch_name and b.id != branch.id):
                raise ValidationError(_('%s already exists, please enter a different branch name!' % branch_name))
