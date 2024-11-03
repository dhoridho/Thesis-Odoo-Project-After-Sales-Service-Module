# -*- coding: utf-8 -*-

from odoo import models, fields

class Company(models.Model):
    _inherit = 'res.company'

    is_post_closing_cashbox_value_in_session = fields.Boolean('Post Closing Cashbox Value in Session', default=True)
