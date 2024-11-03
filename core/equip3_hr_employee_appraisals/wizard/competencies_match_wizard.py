from odoo import fields, models, api

class CompetenciesMatchWizard(models.TransientModel):
	_name = 'competencies.match.wizard'

	name = fields.Char('Name')
	competencies_match_id = fields.Many2one('career.suggestion.competencies.match', string='Job Suggestion')
	suggestion_id = fields.Many2one('employee.career.suggestion', ondelete='cascade')
	job_id = fields.Many2one('hr.job', string='Job Position')
	department_id = fields.Many2one('hr.department', string='Department')
	competency_match = fields.Float('Competency Match (%)')
	# task_id = fields.Many2one('survey.survey', string='Task', domain="[('state','=','open')]")
	task_ids = fields.Many2many('survey.survey', string='Task',domain="[('state','=','open')]")
	deadline = fields.Date('Deadline', required=True, default=fields.Datetime.now)

	@api.model
	def default_get(self, fields):
		res = super(CompetenciesMatchWizard, self).default_get(fields)
		active_id =  self.env.context.get('active_id')
		if active_id:
			match_id = self.env['career.suggestion.competencies.match'].sudo().browse(active_id)
			res.update({'competencies_match_id': match_id.id,
						'suggestion_id':match_id.suggestion_id.id,
						'job_id':match_id.job_id.id,
						'department_id':match_id.department_id.id,
						'competency_match':match_id.competency_match})
		return res

	def action_save(self):
		lines = []
		suggestion_line_id =  self.env['employee.career.suggestion.line'].search([('job_id','=',self.job_id.id),('suggestion_id','=',self.suggestion_id.id),('department_id','=',self.department_id.id)])
		if suggestion_line_id:
			suggestion_line_id.unlink()
		lines.append((0, 0, {'competencies_match_id': self.competencies_match_id.id,
							'suggestion_id': self.suggestion_id.id,
							'job_id': self.job_id.id,
							'department_id': self.department_id.id,
							'competency_match': self.competency_match,
							'deadline': self.deadline,
							'task_ids': self.task_ids.ids,
							  }))
		self.suggestion_id.career_suggestion_ids = lines
		return True



 