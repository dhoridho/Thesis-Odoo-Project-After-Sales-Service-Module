# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_tag_id = fields.Many2one('res.users.tag', string='User Tag')


class ResUsersTag(models.Model):
    _name = 'res.users.tag'
    _description = 'User Tag'

    name = fields.Char(required=True, string='Name')
