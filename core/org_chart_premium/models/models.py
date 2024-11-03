# -*- coding: utf-8 -*-
import base64
import logging
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)

class OrgChartDepartment(models.Model):
	_name = 'org.chart.employee'

	name = fields.Char("Org Chart Employee")

	@api.model
	def get_employee_data(self):
		if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
				company = self.env.user.company_id
				my_employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
				data = {
					'id': -1,
					'name': company.name,
					'title': company.country_id.name,
					'children': [],
					'office': "<img class='avatar company' src='/logo.png' />",
				}
				employees = self.env['hr.employee'].search([
					('parent_id','=',False),
					('company_id','=',company.id),
					('department_id','=',my_employee.department_id.id)

				])
				for employee in employees:
					data['children'].append(self.get_children(employee, 'middle-level'))

				return {'values': data}
		else:
			company = self.env.user.company_id
			data = {
				'id': -1,
				'name': company.name,
				'title': company.country_id.name,
				'children': [],
				'office': "<img class='avatar company' src='/logo.png' />",
			}
			employees = self.env['hr.employee'].search([
				('parent_id','=',False),
				('company_id','=',company.id),
			])
			for employee in employees:
				data['children'].append(self.get_children(employee, 'middle-level'))

			return {'values': data}


	@api.model
	def get_children(self, emp, style=False):
		data = []
		company = self.env.user.company_id
		emp_data = {'id':emp.id ,'name': emp.name, 'title': self._get_position(emp), 'office': self._get_image(emp, style)}
		childrens = self.env['hr.employee'].search([
			('parent_id','=',emp.id),
			('company_id','=',company.id),
		])
		for child in childrens:
			sub_child = self.env['hr.employee'].search([
				('parent_id','=',child.id),
				('company_id','=',company.id),
			])
			next_style= self._get_style(style)
			if not sub_child:
				data.append({'id':child.id ,'name': child.name, 'title': self._get_position(child), 'className': next_style, 'office': self._get_image(child, style)})
			else:
				data.append(self.get_children(child, next_style))

		if childrens:
			emp_data['children'] = data
		if style:
			emp_data['className'] = style

		return emp_data


	def _get_style(self, last_style):
		if last_style == 'middle-level':
			return 'product-dept'
		if last_style == 'product-dept':
			return 'rd-dept'
		if last_style == 'rd-dept':
			return 'pipeline1'
		if last_style == 'pipeline1':
			return 'frontend1'

		return 'middle-level'

	def _get_image(self, emp, style):
		if emp.image_1920:
			image_path = "/web/image/hr.employee/%s/image_1920" %(emp.id)
			return '<img class="avatar %s" src=%s />' % (style, image_path)

		image_path = "/org_chart_premium/static/src/img/default_image.png"
		return '<img class="avatar %s" src=%s />' % (style, image_path)

	def _get_position(self, emp):
		if emp.sudo().job_id:
			return emp.sudo().job_id.name
		return ""

	# Get Dep Form ID
	@api.model
	def get_emp_form_id(self):
		org_chart_config = self.env.ref('org_chart_premium.slife_org_chart_config_data')
		return {
			'form_id': self.env.ref('org_chart_premium.chart_employee_form').id,
			'direction': 'l2r' if org_chart_config.direction == 'horizontal' else False,
			'vertical_level': int(org_chart_config.vertical_level) if org_chart_config.vertical_level != 'none' else False,
		}

class HrEmployee(models.Model):
	_inherit="hr.employee"

	@api.model
	def _default_parent_id(self):
		if self.env.context.get('parent_id') and self.env.context.get('parent_id') > 0:
			return self.env.context.get('parent_id')
		return False

	parent_id = fields.Many2one('hr.employee', 'Manager', default=_default_parent_id)

	@api.depends('department_id')
	def _compute_parent_id(self):
		super(HrEmployee, self)._compute_parent_id()
		if self.env.context.get('parent_id') and self.env.context.get('parent_id') > 0:
			for employee in self:
				employee.parent_id = self.env.context.get('parent_id')

	# @api.multi
	def action_to_save(self):
		return {
			'type': 'ir.actions.client',
			'tag': 'reload',
		}

class SlifeEmployee(models.TransientModel):
	_name = "slife.employee"

	@api.model
	def _default_parent_id(self):
		if self.env.context.get('parent_id') and self.env.context.get('parent_id') > 0:
			return self.env.context.get('parent_id')
		return False

	@api.model
	def _default_childs_number(self):
		if self.env.context.get('childs_number') and self.env.context.get('childs_number') > 0:
			return self.env.context.get('childs_number')
		return False

	@api.model
	def _default_image(self):
		image_path = get_module_resource('org_chart_premium', 'static/src/img', 'default_image.png')
		return base64.b64encode(open(image_path, 'rb').read())

	parent_id = fields.Many2one('hr.employee', string='Employee Parent', default=_default_parent_id, readonly=True)
	parent_image = fields.Binary('Employee Image', default=_default_image, readonly=True)
	new_parent_id = fields.Many2one("hr.employee", string="New Parent")
	new_parent_image = fields.Binary("New Manager Image", readonly=True, default=_default_image)
	childs_number = fields.Integer("Number of Childs", default=_default_childs_number, readonly=True)

	@api.onchange("parent_id")
	def _onchange_parent_id(self):
		if self.parent_id.image_1920:
			self.parent_image = self.parent_id.image_1920
		else:
			self.parent_image = self._default_image()

	@api.onchange("new_parent_id")
	def _onchange_new_parent_id(self):
		if self.new_parent_id.image_1920:
			self.new_parent_image = self.new_parent_id.image_1920
		else:
			self.new_parent_image = self._default_image()

	# @api.multi
	def action_to_save_parent(self):
		for record in self:
			parent = False
			department = record.parent_id.department_id.id
			if record.env.context.get('save') == 'yes':
				if not record.new_parent_id:
					raise ValidationError(_('Please Fill the New Parent Field.'))
				parent = record.new_parent_id.id
				department =  record.new_parent_id.department_id.id
			childs = record.env['hr.employee'].search([('parent_id','=',record.parent_id.id)])
			for child in childs:
				self._change_information(child, department, parent)

		return {
			'type': 'ir.actions.client',
			'tag': 'reload',
		}

	@api.model
	def _change_information(self, child, department_id, parent_id=False):
		for record in self:
			vals = {'department_id': department_id}
			if parent_id:
				vals['parent_id'] = parent_id
			child.write(vals)
			childrens = record.env['hr.employee'].search([('parent_id','=',child.id)])
			for children in childrens:
				self._change_information(children, department_id)


class SlifeOrgChartConfig(models.Model):
	_name = 'slife.org.chart.config'

	name = fields.Char(default='Organization Chart Configiguration')
	direction = fields.Selection([
		('vertical', 'Vertical'),
		('horizontal', 'Horizontal'),
	], string='Default Direction', default='vertical')
	vertical_level = fields.Selection([
		('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'),
		('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('none', 'None')
	], string='Default Vertical Level', default='none')
