# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from . import wizard
from . import models
from . import controllers
from odoo import api, SUPERUSER_ID

def uninstall_hook(cr, registry):
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    activity_rule = env.ref('mail.mail_activity_rule_user')
    if activity_rule:
        activity_rule.write({
            'domain_force':"['|', ('user_id', '=', user.id), ('create_uid', '=', user.id)]"
            })

def _sh_activity_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    activities = env['mail.activity'].sudo().search([])
    if activities:
        for activity in activities:
            activity.sudo().write({
                'active':True
            })
            activity.onchange_state()