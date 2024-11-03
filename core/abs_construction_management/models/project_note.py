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

class ProjectNotes(models.Model):
    _name = 'project.notes'
    _description = "Project Notes"
    _rec_name = 'project_id'

    tag_ids = fields.Many2many('project.tags', string = 'Tags')
    user_id = fields.Many2one('res.users', string = 'Responsible Person')
    project_id = fields.Many2one('project.project', string = 'Project')
    notes = fields.Text(string = 'Notes')
