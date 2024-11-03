# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    task_color = fields.Char(string='Set color index of running task in Kanban')
