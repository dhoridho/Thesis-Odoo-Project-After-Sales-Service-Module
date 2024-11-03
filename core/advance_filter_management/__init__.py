from . import models
from odoo.api import Environment, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    user_ids = []
    for user in env['res.users'].search([]):
        if user.has_group('base.group_user'):
            user_ids.append(user.id)
    env.ref('advance_filter_management.group_filters_user').users = [(6,0,user_ids)]