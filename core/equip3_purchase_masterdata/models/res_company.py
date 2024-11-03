# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # override selection malah nambah value (?)
    record_based_on_purchase = fields.Selection([
        ("purchase", "Order Confirm"),
        ("done", "Done (Closed)"),
        ("both", "Both")],
        string="Price History Based On (Purchase)",
        default="done"
    )