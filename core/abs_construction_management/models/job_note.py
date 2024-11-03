# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2021-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
from odoo import api, fields, models, _

class JobNotes(models.Model):
    _name = 'job.notes'
    _description = "job Notes"
    _rec_name = 'task_id'

    tag_ids = fields.Many2many('project.tags', string = 'Tags')
    user_id = fields.Many2one('res.users', string = 'Responsible Person')
    task_id = fields.Many2one('project.task', string = 'Work Order')
    project_id = fields.Many2one('project.project', string = 'Project')
    task_ids = fields.Many2many('project.task', string = 'Work Orders')
    notes = fields.Text(string = 'Notes')

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            task_list = []
            task_obj = self.env['project.task'].search([('project_id','=',self.project_id.id)])
            if task_obj:
                for task in task_obj:
                    if task:
                        task_list.append(task)
                if task_list:
                    self.task_ids = [(6,0,[v.id for v in task_list])]
