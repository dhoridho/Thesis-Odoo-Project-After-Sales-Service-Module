# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields, registry

_logger = logging.getLogger(__name__)
    
class ResBranch(models.Model):
    _inherit = "res.branch"
    _description = "Branch of shops, like a multi company"

    user_id = fields.Many2one(
        'res.users',
        'Branch Manager',
        #required=1,
        help='Manager of this Branch'
    )
    user_ids = fields.Many2many(
        'res.users',
        'pos_branch_res_users_rel',
        'branch_id',
        'user_id',
        string='Branch Users',
        help='Users have added here, them will see any datas have linked to this Branch'
    )

    def assign_branch_to_users(self):
        for branch in self:
            for user in branch.user_ids:
                user.sudo().write({'pos_branch_id': branch.id})
        return True

    def get_default_branch(self):
        if self.env.user.pos_branch_id:
            return self.env.user.pos_branch_id.id
        else:
            branches = self.sudo().search(['|', ('user_ids','=', self.env.user.id), ('user_id', '=', self.env.user.id)], limit=1)
            if branches:
                return branches.id
            else:
                _logger.info('[get_default_branch] User [ %s ] have not set Branch' % self.env.user.login)
                return None