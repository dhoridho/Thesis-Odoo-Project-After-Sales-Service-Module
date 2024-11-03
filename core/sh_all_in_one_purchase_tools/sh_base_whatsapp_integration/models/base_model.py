# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"


class ResUsers(models.Model):
    _inherit = "res.users"

    sign = fields.Text('Signature')
