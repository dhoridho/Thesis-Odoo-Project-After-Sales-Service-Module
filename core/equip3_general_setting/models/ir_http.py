from odoo import models, fields
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        user = request.env.user

        is_superuser = request.env.su
        if is_superuser:
            user_branches = self.env['res.branch'].sudo().search([('company_id', '=', request.env.user.company_id.id)])
            user_branch = user_branches[0]
        else:
            user_branch = user.branch_id
            user_branches = user.branch_ids

        values = {'branch_id': user_branch.id if request.session.uid else None}
        if user.has_group('base.group_user'):
            values.update({
                'user_branches': {
                    'current_branch': (user_branch.id, user_branch.name, user_branch.company_id.id), 
                    'allowed_branches': [(branch.id, branch.name, branch.company_id.id) for branch in user_branches],
                },
                'display_switch_branch_menu': is_superuser or (user.has_group('branch.group_multi_branch') and len(user_branches) > 1),
            })
        result.update(values)
        return result
