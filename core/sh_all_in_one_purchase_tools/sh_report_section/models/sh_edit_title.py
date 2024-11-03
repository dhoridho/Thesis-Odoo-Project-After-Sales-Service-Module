# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_group_enable_report_section = fields.Boolean(
        "Enable Report Template", implied_group='sh_all_in_one_purchase_tools.sh_group_enable_report_section')

class EditTitle(models.Model):
    _name = "sh.edit.title"
    _description = "Report Template"

    name = fields.Char(string="Name")
