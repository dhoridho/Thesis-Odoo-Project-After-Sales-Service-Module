# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class PurchaseAgreementType(models.Model):
    _name = 'purchase.agreement.type'
    _description = 'Purchase Agreement Type'
    _rec_name = 'name'

    name = fields.Char("Name", required=True)
