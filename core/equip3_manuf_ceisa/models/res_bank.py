# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResBank(models.Model):
    _inherit = "res.bank"

    code = fields.Char('Bank Code', tracking=True)