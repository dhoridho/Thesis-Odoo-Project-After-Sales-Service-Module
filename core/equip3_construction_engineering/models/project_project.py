# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProjectProject(models.Model):
	_inherit = 'project.project'

	construction_type = fields.Selection([('construction','Construction'),('engineering','Engineering')], string="Construction Type", default='construction', required=True)
	
	@api.onchange('construction_type')
	def onchange_department_type_change(self):
		if self.construction_type == 'engineering':
			self.department_type = 'project'

