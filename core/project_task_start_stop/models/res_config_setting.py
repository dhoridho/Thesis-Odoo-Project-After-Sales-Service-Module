# -*- coding: utf-8 -*-

from odoo import models, fields


class ProjectStartStop(models.TransientModel):
    _inherit = 'res.config.settings'

    task_color = fields.Char(string='Set color index of running task in Kanban', related='company_id.task_color', readonly=False)
