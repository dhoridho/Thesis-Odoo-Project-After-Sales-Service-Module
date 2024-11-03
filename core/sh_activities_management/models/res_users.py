# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    sh_activity_access = fields.Selection(
        [('portal_user', 'Activity Portal User'), ('portal_supervisor', 'Activity Portal Supervisor'), ('portal_manager', 'Activity Portal Manager')],default="portal_user",string="Portal Activity access")
