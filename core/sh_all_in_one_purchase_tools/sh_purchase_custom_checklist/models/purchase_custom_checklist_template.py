# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_purchase_checklist = fields.Boolean(
        "Enable Purchase Custom Checklist", implied_group='sh_all_in_one_purchase_tools.group_enable_purchase_checklist')

class PurchaseCustomChecklist(models.Model):
    _name = "purchase.custom.checklist.template"
    _description = "Purchase Custom Checklist Template"

    name = fields.Char("Name", required=True)
    checklist_template = fields.Many2many(
        comodel_name='purchase.custom.checklist',
        relation='checklist_template_table',
        string='CheckList Template')
