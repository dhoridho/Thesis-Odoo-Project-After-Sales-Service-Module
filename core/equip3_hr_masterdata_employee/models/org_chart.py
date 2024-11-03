# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _

class OrgChartDepartment(models.Model):
	_name = 'org.chart.department'

	name = fields.Char("Org Chart Department")

	@api.model
	def get_department_data(self):
		company = self.env.user.company_id
		data = {
			'id': -1,
			'name': company.name,
			'children': [],
			'className': 'company-level'
		}
		HrDepartment = self.env['hr.department'].sudo().search([
			('parent_id','=',False),
			('company_id','=',company.id),
		])
		data['title'] = len(HrDepartment)
		for department in HrDepartment:
			data['children'].append(self.get_dept_children(department, 'dept-level'))

		return {'values': data}

	@api.model
	def get_job_data(self, dept, style=False):
		company = self.env.user.company_id
		data = {
			'id': dept.id,
			'name': dept.name,
			'title': self._get_title_count(dept, 'hr.department'),
			'children': [],
			'className': 'dept-level'
		}
		HrJob = self.env['hr.job'].sudo().search([
			('department_id','=',dept.id),
			('company_id','=',company.id),
			('parent_job_position_id','=',False),
		])
		for job in HrJob:
			data['children'].append(self.get_job_children(job, 'job-level'))

		return data

	@api.model
	def get_job_children(self, job, style=False):
		data = []
		job_data = {}
		company = self.env.user.company_id
		employee_char = ''

		HrEmployee = self.env['hr.employee'].search([('job_id','=',job.id),('company_id','=',company.id),('contract_state','=','open')])
		for employee in HrEmployee:
			employee_char += '● %s <br />' % employee.name
		
		job_data = {
			'id':job.id,
			'name': job.name, 
			'title': self._get_title_count(job, 'hr.job'), 
			'className': 'job-level', 
			'employeeData': employee_char,
		}
		job_childrens = self.env['hr.job'].search([
			('parent_job_position_id','=',job.id),
			('company_id','=',company.id),
		])
		for child in job_childrens:
			sub_child = self.env['hr.job'].search([
				('parent_job_position_id','=',child.id),
				('company_id','=',company.id),
			])

			employee_char = ''
			HrEmployee = self.env['hr.employee'].search([('job_id','=',child.id),('company_id','=',company.id),('contract_state','=','open')])
			for employee in HrEmployee:
				employee_char += '● %s <br />' % employee.name
			
			if not sub_child:
				data.append({
					'id':child.id,
					'name': child.name,
					'title': self._get_title_count(child, 'hr.job'),
					'className': 'job-level',
					'employeeData': employee_char,
				})
			else:
				data.append(self.get_job_children(child, 'job-level'))

		if job_childrens:
			job_data['children'] = data
		if style:
			job_data['className'] = style

		return job_data

	@api.model
	def get_dept_children(self, dept, style=False):
		data = []
		company = self.env.user.company_id
		dept_data = {
			'id':dept.id,
			'name': dept.name,
			'title': self._get_title_count(dept, 'hr.department'),
			'className': 'dept-level'
		}
		dept_childrens = self.env['hr.department'].search([
			('parent_id','=',dept.id),
			('company_id','=',company.id),
		])
		for child in dept_childrens:
			sub_child = self.env['hr.department'].search([
				('parent_id','=',child.id),
				('company_id','=',company.id),
			])
			if not sub_child:
				data.append(self.get_job_data(child, 'job-level'))
			else:
				data.append(self.get_dept_children(child, 'dept-level'))

		job_childrens = self.env['hr.job'].search([
			('department_id','=',dept.id),
			('company_id','=',company.id),
		])
		for child in job_childrens:
			data.append(self.get_job_children(child, 'job-level'))

		if dept_childrens or job_childrens:
			dept_data['children'] = data
		if style:
			dept_data['className'] = style

		return dept_data

	def _get_title_count(self, data, model):
		if model == 'hr.job':
			return str(data.no_of_running_employee)
		elif model == 'hr.department':
			job_count = self.env['hr.job'].search_count([('department_id','=',data.id)])
			return job_count
		return ""