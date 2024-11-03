# -*- coding: utf-8 -*-
from odoo import tools, api, models, _, fields
from odoo.exceptions import UserError
from odoo.tools import config

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        internal_group = self.env.ref('base.group_user')
        count_internal = len(internal_group.users.ids)
        # internal_users_count = sum(1 for user in internal_group.users if user.active)
        user_limits = int(tools.config.get('user_limits', 5))

        if count_internal >= user_limits:
            raise UserError("You cannot add new internal users. You have reached the maximum limit of %s users." % count_internal)
        res = super(ResUsers, self).create(vals)
        return res

    def toggle_active(self):
        internal_group = self.env.ref('base.group_user')
        for user in self:
            if not user.active:
                active_users_count = self.env['res.users'].search_count([
                    ('active', '=', True),
                    ('groups_id', '=', internal_group.id),
                ])
                user_limits = int(tools.config.get('user_limits', 5))
                if active_users_count >= user_limits:
                    raise UserError("You cannot add new active users. You have reached the maximum limit of %s users." % user_limits)

        return super(ResUsers, self).toggle_active()

