# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _

class JobTechnicalTestLine(models.Model):
	_name = "job.technical.test"
	
	name = fields.Char("Technical Test")

class JobTechnicalTestLine(models.Model):
	_name = "job.technical.test.line"
	
	technical_test_id = fields.Many2one('job.technical.test', 'Technical Test')
	job_id = fields.Many2one('hr.job')
	stage_id = fields.Many2one('hr.recruitment.stage', 'Stages', domain=[])
	min_qualification = fields.Integer("Minimum Score")
	stage_failed = fields.Many2one('hr.recruitment.stage', 'If Fail Move To', domain=[])
	remarks = fields.Text('Remarks')
	
	@api.model
	def create(self, vals):
		res = super(JobTechnicalTestLine, self).create(vals)
		if not res.stage_failed:
			res.stage_failed = self.env['hr.recruitment.stage'].search([('name', '=', 'Reject')])
		return res
	
	@api.model
	def write(self, vals):
		res = super(JobTechnicalTestLine, self).write(vals)
		if not self.stage_failed:
			self.stage_failed = self.env['hr.recruitment.stage'].search([('name', '=', 'Reject')])
		return res