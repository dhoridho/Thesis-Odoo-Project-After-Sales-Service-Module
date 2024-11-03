# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api

class PurchaseCustomChecklist(models.Model):
    _inherit = "purchase.custom.checklist.template"
    _description = "Purchase Custom Checklist Template"

    order = fields.Selection([
        ('goods', 'Goods Order'),
        ('services', 'Services Order'),
        ('milestone', 'Milestone'),
    ], string='Orders')
    order_type = fields.Boolean("Type", compute="_compute_order_type")
    trigger = fields.Integer("Trigger", default=1)

    @api.depends('trigger', 'name')
    def _compute_order_type(self):
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
        # if self.env.company.is_good_services_order:
            self.order_type = True
        else:
            self.order_type = False
