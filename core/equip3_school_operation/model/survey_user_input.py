from odoo import api, fields, models, _


class SurveyUserInput(models.Model):
	_inherit = "survey.user_input"

	assignment_id = fields.Many2one("school.student.assignment", string="Assignment")
	exam_id = fields.Many2one("exam.exam", string="Exam")
	additional_id = fields.Many2one("additional.exam.line", string="Additional Exam")

