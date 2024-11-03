# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_credit = fields.Boolean('Set Customer Credit Limit ?')
    customer_credit_limit = fields.Float('Customer Credit Limit')
    set_customer_onhold = fields.Boolean(
        'Set Customer On Hold (Credit Limit Exceed)')
