# -*- coding: utf-8 -*-
import pytz
from datetime import datetime
from odoo import fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class ProjectTaskDescription(models.TransientModel):
    _name = 'project.task.description'
    _description = "Project Task Description"

    description = fields.Char(string='Task Description', required=True)

    def button_start(self):
        active_model = self.env.context.get('active_model')
        task_id = self.env[active_model].browse(self.env.context.get('active_id'))
        tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        task = task_id.work_id.create({
                'user_id': self.env.user.id,
                'start_date': datetime.now(tz).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'description': self.description,
                'task_id': task_id.id
                })
        task_id.status = 'start'
        return task
