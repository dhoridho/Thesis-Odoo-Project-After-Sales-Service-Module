# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.users'

    is_tendor_vendor = fields.Boolean('Is Tender Portal User')
