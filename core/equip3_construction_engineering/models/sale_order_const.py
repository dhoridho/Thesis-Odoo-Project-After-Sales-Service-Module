# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class SaleOrderConst(models.Model):
	_inherit = 'sale.order.const'

	is_engineering = fields.Boolean('Engineering', readonly=True)
	manufacture_line = fields.One2many('sale.manufacture.line','sale_cons_id')
	adjustment_type = fields.Selection(selection_add=[('manuf', 'To Manufacture')], string='Adjustment Applies to',default='global', readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
	discount_type = fields.Selection(selection_add=[('manuf', 'To Manufacture')], string='Discount Applies to', default='global', readonly=True,
                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'to_approve': [('readonly', False)], 'waiting_for_over_limit_approval': [('readonly', False)], 
                           'over_limit_approved': [('readonly', False)]}) 
	adjustment_manuf = fields.Float(string="Manufacturing Adjustment (+)")
	discount_manuf = fields.Float(string="Manufacturing Discount (-)")
	hide_cascade = fields.Boolean('Hide cascade button', default=True, compute='_compute_hide_cascade')

	@api.onchange('project_id')
	def onchange_project_quatation_enginerring(self):
		if self.project_id:
			self.is_engineering = False
			if self.project_id.construction_type == 'engineering':
				self.is_engineering = True
			else:
				self.is_engineering = False

	@api.onchange('is_engineering', 'adjustment_type', 'discount_type')
	def onchange_is_engineering(self):
		for res in self:
			if res.is_engineering == False:
				if res.adjustment_type == 'manuf':
					raise ValidationError(_("Cannot use this adjustment type because this project is not engineering type"))
					res.adjustment_type == 'global'
				if res.discount_type == 'manuf':
					raise ValidationError(_("Cannot use this discount type because this project is not engineering type"))
					res.discount_type == 'global'

	@api.onchange("job_references")
	def _onchange_job_reference_many2many(self):
		context = self._context
		is_wizard = context.get('is_wizard')
		if is_wizard or self.is_wizard:
			job_reference = context.get('default_job_references')
			if job_reference:
				job_count = len(job_reference)
			else:
				job_count = self.job_count
			if len(self.job_references) > job_count:
				raise ValidationError(_("The addition of a new BOQ does not affect the quotation value. You need to make a new quotation for that BOQ."))
			# elif len(self.job_references) == job_count - 1:
			# 	raise ValidationError(_("You can't delete the default BOQ."))
			for job in job_reference:
				if job[1] not in self.job_references._origin.ids:
					raise ValidationError(_("You can't delete the default BOQ."))
			
		if self.job_references:
			job = self.job_references
			self.project_id = job[0].project_id.id
			self.partner_id = job[0].partner_id.id
			self.client_order_ref = job[0].customer_ref
			self.analytic_idz = job[0].analytic_idz
			self.start_date = job[0].start_date
			self.end_date = job[0].end_date
			self.contract_category = job[0].contract_category
			self.main_contract_ref = job[0].main_contract_ref
			self.warehouse_address = job[0].warehouse_address

			if not (self.is_wizard or is_wizard):
				scope = []
				section = []
				variable = []
				manufacture = []
				material_lines = []
				labour_lines = []
				overhead_lines = []
				asset_lines = []
				equipment_lines = []
				subcon_lines = []
				self.project_scope_ids = False
				self.section_ids = False
				self.variable_ids = False
				self.manufacture_line = False
				self.material_line_ids = False
				self.labour_line_ids = False
				self.internal_asset_line_ids = False
				self.overhead_line_ids = False
				self.equipment_line_ids = False
				self.subcon_line_ids = False
				scope_vals = []
				sect_vals = []
				var_vals = []
				manuf_vals = []
				mat_vals = []
				lab_vals = []
				ov_vals = []
				asset_vals = []
				equip_vals = []
				sub_vals = []
				for line in self.job_references:
					if line.project_scope_ids:
						for sco in line.project_scope_ids:
							value = {
								"project_scope": sco.project_scope.name,
								"description": sco.description
							}
							if value not in scope_vals:
								scope.append((0, 0, {
									"project_scope": sco.project_scope and sco.project_scope.id or False,
									"description": sco.description,
									"subtotal_scope": sco.subtotal,
								}))
								scope_vals.append(value)
							else:
								idx = scope_vals.index(value)
								scope[idx][2]['subtotal_scope'] += sco.subtotal

					
					if line.section_ids:
						for sec in line.section_ids:
							value = {
								"project_scope": sec.project_scope.name,
								"section": sec.section_name.name,
								"description": sec.description,
								"uom_id": sec.uom_id.id
							}
							if value not in sect_vals:
								section.append((0, 0, {
									"project_scope": sec.project_scope and sec.project_scope.id or False,
									"section": sec.section_name or sec.section_name.id or False,
									"description": sec.description,
									"quantity": sec.quantity,
									"uom_id": sec.uom_id or sec.uom_id.id or False,
									"subtotal_section": sec.subtotal,
								}))
								sect_vals.append(value)
							else:
								idx = sect_vals.index(value)
								section[idx][2]['subtotal_section'] += sec.subtotal
								section[idx][2]['quantity'] += sec.quantity

					if line.variable_ids:
						for var in line.variable_ids:
							value = {
								"project_scope": var.project_scope.name,
								"section": var.section_name.name,
								"variable": var.variable_name.name,
								"uom_id": var.variable_uom.id
							}
							if value not in var_vals:
								variable.append((0, 0, {
									"project_scope": var.project_scope and var.project_scope.id or False,
									"section": var.section_name or var.section_name.id or False,
									"variable": var.variable_name or var.variable_name.id or False,
									"quantity": var.variable_quantity,
									"uom_id": var.variable_uom or var.variable_uom.id or False,
									"subtotal_variable": var.subtotal,
								}))
								var_vals.append(value)
							else:
								idx = var_vals.index(value)
								variable[idx][2]['subtotal_variable'] += var.subtotal
								variable[idx][2]['quantity'] += var.variable_quantity
					
					if line.manufacture_line:
						for manuf in line.manufacture_line:
							value = {
								"project_scope": manuf.project_scope_id.name,
								"section": manuf.section_id.name,
								"variable_ref": manuf.variable_ref.name,
								"finish_good_id": manuf.finish_good_id.name,
								"bom_id": manuf.bom_id.name,
								"uom_id": manuf.uom.id
							}
							if value not in manuf_vals:
								manufacture.append((0, 0, {
									"project_scope": manuf.project_scope_id and manuf.project_scope_id.id or False,
									"section": manuf.section_id or manuf.section_id.id or False,
									"variable_ref": manuf.variable_ref or manuf.variable_ref.id or False,
									"finish_good_id": manuf.finish_good_id or manuf.finish_good_id.id or False,
									"bom_id": manuf.bom_id or manuf.bom_id.id or False,
									"quantity": manuf.quantity,
									"uom_id": manuf.uom or manuf.uom.id or False,
									"subtotal_manuf": manuf.subtotal,
								}))
								manuf_vals.append(value)
							else:
								idx = manuf_vals.index(value)
								manufacture[idx][2]['subtotal_manuf'] += manuf.subtotal
								manufacture[idx][2]['quantity'] += manuf.quantity

					if line.material_estimation_ids:
						for material in line.material_estimation_ids:
							if self.is_engineering == False:
								value = {
									"project_scope": material.project_scope.name,
									"section_name": material.section_name.name,
									"variable_ref": material.variable_ref.name,
									"type": "material",
									"group_of_product": material.group_of_product.id,
									"material_id": material.product_id.id,
									"description": material.description,
									"uom_id": material.uom_id.id,
									"unit_price": material.unit_price
								}
							else:
								value = {
									"project_scope": material.project_scope.name,
									"section_name": material.section_name.name,
									"variable_ref": material.variable_ref.name,
									"type": "material",
									"group_of_product": material.group_of_product.id,
									"finish_good_id": material.finish_good_id.name,
									"bom_id": material.bom_id.name,
									"material_id": material.product_id.id,
									"description": material.description,
									"uom_id": material.uom_id.id,
									"unit_price": material.unit_price
								}	
							if value not in mat_vals:
								material_lines.append((0, 0, {
									"project_scope": material.project_scope and material.project_scope.id or False,
									"section_name": material.section_name and material.section_name.id or False,
									"variable_ref": material.variable_ref and material.variable_ref.id or False,
									"type": "material",
									"finish_good_id": material.finish_good_id or material.finish_good_id.id or False,
									"bom_id": material.bom_id or material.bom_id.id or False,
									"group_of_product": material.group_of_product and material.group_of_product.id or False,
									"material_id": material.product_id and material.product_id.id or False,
									"description": material.description,
									"analytic_idz": material.analytic_idz and [(6, 0, material.analytic_idz.ids)] or False,
									"quantity": material.quantity,
									"uom_id": material.uom_id and material.uom_id.id or False,
									"unit_price": material.unit_price,
									"subtotal": material.subtotal,
								}))
								mat_vals.append(value)
							else:
								idx = mat_vals.index(value)
								if value['unit_price'] > material_lines[idx][2]['unit_price']:
									material_lines[idx][2]['unit_price'] = value['unit_price']

								material_lines[idx][2]['quantity'] += material.quantity
								material_lines[idx][2]['subtotal'] += material.subtotal
					
					if line.labour_estimation_ids:
						for labour in line.labour_estimation_ids:
							if self.is_engineering == False:
								value = {
									"project_scope": labour.project_scope.name,
									"section_name": labour.section_name.name,
									"variable_ref": labour.variable_ref.name,
									"type": "labour",
									"group_of_product": labour.group_of_product.id,
									"labour_id": labour.product_id.id,
									"description": labour.description,
									"uom_id": labour.uom_id.id,
									"unit_price": labour.unit_price
								}
							else:
								value = {
									"project_scope": labour.project_scope.name,
									"section_name": labour.section_name.name,
									"variable_ref": labour.variable_ref.name,
									"type": "labour",
									"group_of_product": labour.group_of_product.id,
									"finish_good_id": labour.finish_good_id.name,
									"bom_id": labour.bom_id.name,
									"labour_id": labour.product_id.id,
									"description": labour.description,
									"uom_id": labour.uom_id.id,
									"unit_price": labour.unit_price
								}
									
							if value not in lab_vals:
								labour_lines.append((0, 0, {
									"project_scope": labour.project_scope and labour.project_scope.id or False,
									"section_name": labour.section_name and labour.section_name.id or False,
									"variable_ref": labour.variable_ref and labour.variable_ref.id or False,
									"type": "labour",
									"group_of_product": labour.group_of_product and labour.group_of_product.id or False,
									"finish_good_id": labour.finish_good_id or labour.finish_good_id.id or False,
									"bom_id": labour.bom_id or labour.bom_id.id or False,
									"labour_id": labour.product_id and labour.product_id.id or False,
									"description": labour.description,
									"analytic_idz": labour.analytic_idz and [(6, 0, labour.analytic_idz.ids)] or False,
									"contractors": labour.contractors,
									"time": labour.time,
									"quantity": labour.quantity,
									"uom_id": labour.uom_id and labour.uom_id.id or False,
									"unit_price": labour.unit_price,
									"subtotal": labour.subtotal,
								}))
								lab_vals.append(value)
							else:
								idx = lab_vals.index(value)
								
								if value['unit_price'] > labour_lines[idx][2]['unit_price']:
									labour_lines[idx][2]['unit_price'] = value['unit_price']

								labour_lines[idx][2]['quantity'] += labour.quantity
								labour_lines[idx][2]['subtotal'] += labour.subtotal
								labour_lines[idx][2]['contractors'] += labour.contractors
								labour_lines[idx][2]['time'] += labour.time
					
					if line.overhead_estimation_ids:
						for overhead in line.overhead_estimation_ids:
							if self.is_engineering == False:
								value = {
									"project_scope": overhead.project_scope.name,
									"section_name": overhead.section_name.name,
									"variable_ref": overhead.variable_ref.name,
									"type": "overhead",
									"group_of_product": overhead.group_of_product.id,
									"overhead_id": overhead.product_id.id,
									"description": overhead.description,
									"uom_id": overhead.uom_id.id,
									"unit_price": overhead.unit_price
								}
							else:
								value = {
									"project_scope": overhead.project_scope.name,
									"section_name": overhead.section_name.name,
									"variable_ref": overhead.variable_ref.name,
									"type": "overhead",
									"finish_good_id": overhead.finish_good_id.name,
									"bom_id": overhead.bom_id.name,
									"group_of_product": overhead.group_of_product.id,
									"overhead_id": overhead.product_id.id,
									"description": overhead.description,
									"uom_id": overhead.uom_id.id,
									"unit_price": overhead.unit_price
								}

							if value not in ov_vals:
								overhead_lines.append((0, 0, {
									"project_scope": overhead.project_scope and overhead.project_scope.id or False,
									"section_name": overhead.section_name and overhead.section_name.id or False,
									"variable_ref": overhead.variable_ref and overhead.variable_ref.id or False,
									"type": "overhead",
									"group_of_product": overhead.group_of_product and overhead.group_of_product.id or False,
									"finish_good_id": overhead.finish_good_id or overhead.finish_good_id.id or False,
									"bom_id": overhead.bom_id or overhead.bom_id.id or False,
									"overhead_id": overhead.product_id and overhead.product_id.id or False,
									"description": overhead.description,
									"analytic_idz": overhead.analytic_idz and [(6, 0, overhead.analytic_idz.ids)] or False,
									"quantity": overhead.quantity,
									"uom_id": overhead.uom_id and overhead.uom_id.id or False,
									"unit_price": overhead.unit_price,
									"subtotal": overhead.subtotal,
								}))
								ov_vals.append(value)
							else:
								idx = ov_vals.index(value)
								if value['unit_price'] > overhead_lines[idx][2]['unit_price']:
									overhead_lines[idx][2]['unit_price'] = value['unit_price']

								overhead_lines[idx][2]['quantity'] += overhead.quantity
								overhead_lines[idx][2]['subtotal'] += overhead.subtotal
					
					if line.internal_asset_ids:
						for asset in line.internal_asset_ids:
							if self.is_engineering == False:
								value = {
									'project_scope': asset.project_scope.name,
									'section_name': asset.section_name.name,
									'variable_ref': asset.variable_ref.name,
									'type': 'asset',
									'asset_category_id': asset.asset_category_id.id,
									'asset_id': asset.asset_id.id,
									'description': asset.description,
									'uom_id': asset.uom_id.id,
									'unit_price': asset.unit_price
								}
							else:
								value = {
									'project_scope': asset.project_scope.name,
									'section_name': asset.section_name.name,
									'variable_ref': asset.variable_ref.name,
									'type': 'asset',
									"finish_good_id": asset.finish_good_id.name,
									"bom_id": asset.bom_id.name,
									'asset_category_id': asset.asset_category_id.id,
									'asset_id': asset.asset_id.id,
									'description': asset.description,
									'uom_id': asset.uom_id.id,
									'unit_price': asset.unit_price
								}
								
							if value not in asset_vals:
								asset_lines.append((0, 0, {
									'project_scope': asset.project_scope and asset.project_scope.id or False,
									'section_name': asset.section_name and asset.section_name.id or False,
									'variable_ref': asset.variable_ref and asset.variable_ref.id or False,
									'type': 'asset',
									"finish_good_id": asset.finish_good_id or asset.finish_good_id.id or False,
									"bom_id": asset.bom_id or asset.bom_id.id or False,
									'asset_category_id': asset.asset_category_id and asset.asset_category_id.id or False,
									'asset_id': asset.asset_id and asset.asset_id.id or False,
									'description': asset.description,
									'analytic_idz': asset.analytic_idz and [(6, 0, asset.analytic_idz.ids)] or False,
									'quantity': asset.quantity,
									'uom_id': asset.uom_id and asset.uom_id.id or False,
									'unit_price': asset.unit_price,
									'subtotal': asset.subtotal,
								}))
								asset_vals.append(value)
							else:
								idx = asset_vals.index(value)
								if value['unit_price'] > asset_lines[idx][2]['unit_price']:
									asset_lines[idx][2]['unit_price'] = value['unit_price']

								asset_lines[idx][2]['quantity'] += asset.quantity
								asset_lines[idx][2]['subtotal'] += asset.subtotal

					if line.equipment_estimation_ids:
						for equipment in line.equipment_estimation_ids:
							if self.is_engineering == False:
								value = {
									"project_scope": equipment.project_scope.name,
									"section_name": equipment.section_name.name,
									"variable_ref": equipment.variable_ref.name,
									"type": "equipment",
									"group_of_product": equipment.group_of_product.id,
									"equipment_id": equipment.product_id.id,
									"description": equipment.description,
									"uom_id": equipment.uom_id and equipment.uom_id.id,
									"unit_price": equipment.unit_price
								}
							else:
								value = {
									"project_scope": equipment.project_scope.name,
									"section_name": equipment.section_name.name,
									"variable_ref": equipment.variable_ref.name,
									"type": "equipment",
									"finish_good_id": equipment.finish_good_id.name,
									"bom_id": equipment.bom_id.name,
									"group_of_product": equipment.group_of_product.id,
									"equipment_id": equipment.product_id.id,
									"description": equipment.description,
									"uom_id": equipment.uom_id and equipment.uom_id.id,
									"unit_price": equipment.unit_price
								}

							if value not in equip_vals:
								equipment_lines.append((0, 0, {
									"project_scope": equipment.project_scope and equipment.project_scope.id or False,
									"section_name": equipment.section_name and equipment.section_name.id or False,
									"variable_ref": equipment.variable_ref and equipment.variable_ref.id or False,
									"type": "equipment",
									"group_of_product": equipment.group_of_product and equipment.group_of_product.id or False,
									"finish_good_id": equipment.finish_good_id or equipment.finish_good_id.id or False,
									"bom_id": equipment.bom_id or equipment.bom_id.id or False,
									"equipment_id": equipment.product_id and equipment.product_id.id or False,
									"description": equipment.description,
									"analytic_idz": equipment.analytic_idz and [(6, 0, equipment.analytic_idz.ids)] or False,
									"quantity": equipment.quantity,
									"uom_id": equipment.uom_id and equipment.uom_id.id or False,
									"unit_price": equipment.unit_price,
									"subtotal": equipment.subtotal,
								}))
								equip_vals.append(value)
							else:
								idx = equip_vals.index(value)
								if value['unit_price'] > equipment_lines[idx][2]['unit_price']:
									equipment_lines[idx][2]['unit_price'] = value['unit_price']

								equipment_lines[idx][2]['quantity'] += equipment.quantity
								equipment_lines[idx][2]['subtotal'] += equipment.subtotal
					
					if line.subcon_estimation_ids:
						for subcon in line.subcon_estimation_ids:
							if self.is_engineering == False:
								value = {
									"project_scope": subcon.project_scope.name,
									"section_name": subcon.section_name.name,
									"variable_ref": subcon.variable_ref.name,
									"type": "subcon",
									"subcon_id": subcon.variable.id,
									"description": subcon.description,
									"uom_id": subcon.uom_id.id,
									"unit_price": subcon.unit_price
								}
							else:
								value = {
									"project_scope": subcon.project_scope.name,
									"section_name": subcon.section_name.name,
									"variable_ref": subcon.variable_ref.name,
									"type": "subcon",
									"finish_good_id": subcon.finish_good_id.name,
									"bom_id": subcon.bom_id.name,
									"subcon_id": subcon.variable.id,
									"description": subcon.description,
									"uom_id": subcon.uom_id.id,
									"unit_price": subcon.unit_price
								}

							if value not in sub_vals:
								subcon_lines.append((0, 0, {
									"project_scope": subcon.project_scope and subcon.project_scope.id or False,
									"section_name": subcon.section_name and subcon.section_name.id or False,
									"variable_ref": subcon.variable_ref and subcon.variable_ref.id or False,
									"type": "subcon",
									"finish_good_id": subcon.finish_good_id or subcon.finish_good_id.id or False,
									"bom_id": subcon.bom_id or subcon.bom_id.id or False,
									"subcon_id": subcon.variable and subcon.variable.id or False,
									"description": subcon.description,
									"analytic_idz": subcon.analytic_idz and [(6, 0, subcon.analytic_idz.ids)] or False,
									"quantity": subcon.quantity,
									"uom_id": subcon.uom_id and subcon.uom_id.id or False,
									"unit_price": subcon.unit_price,
									"subtotal": subcon.subtotal,
								}))
								sub_vals.append(value)
							else:
								idx = sub_vals.index(value)
								if value['unit_price'] > subcon_lines[idx][2]['unit_price']:
									subcon_lines[idx][2]['unit_price'] = value['unit_price']
									
								subcon_lines[idx][2]['quantity'] += subcon.quantity
								subcon_lines[idx][2]['subtotal'] += subcon.subtotal
						
				if len(scope) > 0:
					self.project_scope_ids = scope
				if len(section) > 0:
					self.section_ids = section
				if len(variable) > 0:
					self.variable_ids = variable
				if len(manufacture) > 0:
					self.manufacture_line = manufacture
				if len(material_lines) > 0:
					self.material_line_ids = material_lines
				if len(labour_lines) > 0:
					self.labour_line_ids = labour_lines
				if len(overhead_lines) > 0:
					self.overhead_line_ids = overhead_lines
				if len(asset_lines) > 0:
					self.internal_asset_line_ids = asset_lines
				if len(equipment_lines) > 0:
					self.equipment_line_ids = equipment_lines
				if len(subcon_lines) > 0:
					self.subcon_line_ids = subcon_lines

			elif self.is_wizard or is_wizard:
				self.project_scope_ids = False
				self.section_ids = False
				self.variable_ids = False
				if self.is_engineering:
					self.manufacture_line = False

				self.material_line_ids = False
				self.labour_line_ids = False
				self.overhead_line_ids = False
				self.internal_asset_line_ids = False
				self.equipment_line_ids = False
				self.subcon_line_ids = False

				self.project_scope_ids = context.get('default_project_scope_ids')
				self.section_ids = context.get('default_section_ids')
				self.variable_ids = context.get('default_variable_ids')
				if self.is_engineering:
					self.manufacture_line = context.get('default_manufacture_line')

				self.material_line_ids = context.get('default_material_line_ids')
				self.labour_line_ids = context.get('default_labour_line_ids')
				self.overhead_line_ids = context.get('default_overhead_line_ids')
				self.internal_asset_line_ids = context.get('default_internal_asset_line_ids')
				self.equipment_line_ids = context.get('default_equipment_line_ids')
				self.subcon_line_ids = context.get('default_subcon_line_ids')


	def _compute_hide_cascade(self):
		for res in self:
			if res.manufacture_line:
				for line in res.manufacture_line:
					if line.cascaded == False:
						res.hide_cascade = False
						return
				res.hide_cascade = True
				return
			else:
				res.hide_cascade = True
				return

	@api.depends('is_set_adjustment_sale','material_line_ids.subtotal','labour_line_ids.subtotal','overhead_line_ids.subtotal','subcon_line_ids.subtotal', 
					'equipment_line_ids.subtotal', 'internal_asset_line_ids.subtotal', 'material_line_ids.adjustment_method_line', 'labour_line_ids.adjustment_method_line','overhead_line_ids.adjustment_method_line',
					'subcon_line_ids.adjustment_method_line', 'equipment_line_ids.adjustment_method_line', 'internal_asset_line_ids.adjustment_method_line', 
					'material_line_ids.adjustment_amount_line','labour_line_ids.adjustment_amount_line', 'overhead_line_ids.adjustment_amount_line', 
					'subcon_line_ids.adjustment_amount_line', 'equipment_line_ids.adjustment_amount_line', 'internal_asset_line_ids.adjustment_amount_line', 
					'material_line_ids.discount_method_line','labour_line_ids.discount_method_line', 'overhead_line_ids.discount_method_line', 'subcon_line_ids.discount_method_line', 
					'equipment_line_ids.discount_method_line', 'internal_asset_line_ids.discount_method_line', 'material_line_ids.discount_amount_line','labour_line_ids.discount_amount_line',
					'overhead_line_ids.discount_amount_line', 'subcon_line_ids.discount_amount_line', 'equipment_line_ids.discount_amount_line', 'internal_asset_line_ids.discount_amount_line',
					'material_line_ids.project_scope','labour_line_ids.project_scope','overhead_line_ids.project_scope', 'subcon_line_ids.project_scope', 'equipment_line_ids.project_scope', 
					'internal_asset_line_ids.project_scope', 'material_line_ids.section_name','labour_line_ids.section_name', 'overhead_line_ids.section_name', 'subcon_line_ids.section_name', 
					'equipment_line_ids.section_name', 'internal_asset_line_ids.section_name', 'material_line_ids.variable_ref','labour_line_ids.variable_ref',
					'overhead_line_ids.variable_ref', 'subcon_line_ids.variable_ref', 'equipment_line_ids.variable_ref', 'internal_asset_line_ids.variable_ref',
					'adjustment_type', 'adjustment_method_global', 'adjustment_amount_global', 'discount_method_global', 'discount_amount_global', 'discount_type', 
					'project_scope_ids.project_scope', 'project_scope_ids.subtotal_scope', 'project_scope_ids.adjustment_method_scope', 'project_scope_ids.adjustment_amount_scope',
					'project_scope_ids.discount_method_scope', 'project_scope_ids.discount_amount_scope', 'section_ids.project_scope', 
					'section_ids.section', 'section_ids.subtotal_section', 'section_ids.adjustment_method_section', 'section_ids.adjustment_amount_section',
					'section_ids.discount_method_section', 'section_ids.discount_amount_section', 'variable_ids.project_scope', 
					'variable_ids.section', 'variable_ids.variable', 'variable_ids.subtotal_variable', 'variable_ids.adjustment_method_variable', 
					'variable_ids.adjustment_amount_variable', 'variable_ids.discount_method_variable', 'variable_ids.discount_amount_variable',
					'manufacture_line.project_scope', 'manufacture_line.section', 'manufacture_line.finish_good_id', 'manufacture_line.bom_id', 'manufacture_line.subtotal_manuf', 
                    'manufacture_line.adjustment_method_manuf', 'manufacture_line.adjustment_amount_manuf', 'manufacture_line.discount_method_manuf', 'manufacture_line.discount_amount_manuf',
					'material_line_ids.amount_line', 'labour_line_ids.amount_line', 'overhead_line_ids.amount_line', 
					'subcon_line_ids.amount_line', 'equipment_line_ids.amount_line', 'internal_asset_line_ids.amount_line',
					'material_line_ids.line_tax_id', 'labour_line_ids.line_tax_id', 'overhead_line_ids.line_tax_id', 
					'subcon_line_ids.line_tax_id', 'equipment_line_ids.line_tax_id', 'internal_asset_line_ids.line_tax_id')
	def _compute_amount(self):
		for order in self:
			order.contract_amount = 0
			order.total_material = sum(order.material_line_ids.mapped('subtotal'))
			order.total_labour = sum(order.labour_line_ids.mapped('subtotal'))
			order.total_overhead = sum(order.overhead_line_ids.mapped('subtotal'))
			order.total_internal_asset = sum(order.internal_asset_line_ids.mapped('subtotal'))
			order.total_equipment = sum(order.equipment_line_ids.mapped('subtotal'))
			order.total_subcon = sum(order.subcon_line_ids.mapped('subtotal'))
			order.total_asset = sum(order.internal_asset_line_ids.mapped('subtotal')) + sum(order.equipment_line_ids.mapped('subtotal'))
			order.amount_untaxed = sum(order.material_line_ids.mapped('subtotal')) + sum(order.labour_line_ids.mapped('subtotal')) + sum(order.overhead_line_ids.mapped('subtotal')) + sum(order.subcon_line_ids.mapped('subtotal')) + sum(order.internal_asset_line_ids.mapped('subtotal')) + sum(order.equipment_line_ids.mapped('subtotal'))
			order._set_tax_id_lines()

			if order.adjustment_type == 'global':
				# order.adjustment_scope = 0
				# order.adjustment_section = 0
				# order.adjustment_variable = 0
				# order.adjustment_manuf = 0
				# order.line_adjustment = 0
				if order.adjustment_method_global == 'fix':
					order.adjustment_sub = order.adjustment_amount_global
					number_of_lines = len(order.material_line_ids) + len(order.labour_line_ids) + len(order.overhead_line_ids) + len(order.internal_asset_line_ids) + len(order.equipment_line_ids) + len(order.subcon_line_ids)
					number_of_lines_scope = len(order.project_scope_ids)
					number_of_lines_section = len(order.section_ids)
					number_of_lines_variable = len(order.variable_ids)
					number_of_lines_manuf = len(order.manufacture_line)
					for line in order.material_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for line in order.labour_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for line in order.overhead_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for line in order.internal_asset_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for line in order.equipment_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for line in order.subcon_line_ids:
						line_adjustment_line = order.adjustment_amount_global / number_of_lines
						line.sudo().write({'adjustment_line': line_adjustment_line})
					for scope in order.project_scope_ids:
						line_adjustment_scope = order.adjustment_amount_global / number_of_lines_scope
						scope.sudo().write({'scope_adjustment': line_adjustment_scope})
					for section in order.section_ids:
						line_adjustment_section = order.adjustment_amount_global / number_of_lines_section
						section.sudo().write({'section_adjustment': line_adjustment_section})
					for variable in order.variable_ids:
						line_adjustment_variable = order.adjustment_amount_global / number_of_lines_variable
						variable.sudo().write({'variable_adjustment': line_adjustment_variable})
					for manuf in order.manufacture_line:
						line_adjustment_manuf = order.adjustment_amount_global / number_of_lines_manuf
						manuf.sudo().write({'manuf_adjustment': line_adjustment_manuf})

				else:
					if order.is_set_adjustment_sale == False:
						order.adjustment_sub = order.amount_untaxed * (order.adjustment_amount_global/100)
						for line in order.material_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.labour_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.overhead_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.internal_asset_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.equipment_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.subcon_line_ids:
							line_adjustment_line = line.subtotal * (order.adjustment_amount_global/100)
							line.sudo().write({'adjustment_line': line_adjustment_line})                    
						for scope in order.project_scope_ids:
							line_adjustment_scope = scope.subtotal_scope * (order.adjustment_amount_global/100)
							scope.sudo().write({'scope_adjustment': line_adjustment_scope})
						for section in order.section_ids:
							line_adjustment_section = section.subtotal_section * (order.adjustment_amount_global/100)
							section.sudo().write({'section_adjustment': line_adjustment_section})
						for variable in order.variable_ids:
							line_adjustment_variable = variable.subtotal_variable * (order.adjustment_amount_global/100)
							variable.sudo().write({'variable_adjustment': line_adjustment_variable})
						for manuf in order.manufacture_line:
							line_adjustment_manuf = manuf.subtotal_manuf * (order.adjustment_amount_global/100)
							manuf.sudo().write({'manuf_adjustment': line_adjustment_manuf})
					else:
						order.adjustment_sub = (order.amount_untaxed / (1 - (order.adjustment_amount_global / 100))) - order.amount_untaxed
						for line in order.material_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.labour_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.overhead_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.internal_asset_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.equipment_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})
						for line in order.subcon_line_ids:
							line_adjustment_line = (line.subtotal / (1 - (order.adjustment_amount_global / 100))) - line.subtotal
							line.sudo().write({'adjustment_line': line_adjustment_line})                    
						for scope in order.project_scope_ids:
							line_adjustment_scope = (scope.subtotal_scope / (1 - (order.adjustment_amount_global / 100))) - scope.subtotal_scope
							scope.sudo().write({'scope_adjustment': line_adjustment_scope})
						for section in order.section_ids:
							line_adjustment_section = (section.subtotal_section / (1 - (order.adjustment_amount_global / 100))) - section.subtotal_section
							section.sudo().write({'section_adjustment': line_adjustment_section})
						for variable in order.variable_ids:
							line_adjustment_variable = (variable.subtotal_variable / (1 - (order.adjustment_amount_global / 100))) - variable.subtotal_variable
							variable.sudo().write({'variable_adjustment': line_adjustment_variable})
						for manuf in order.manufacture_line:
							line_adjustment_manuf = (manuf.subtotal_manuf / (1 - (order.adjustment_amount_global / 100))) - manuf.subtotal_manuf
							manuf.sudo().write({'manuf_adjustment': line_adjustment_manuf})

			elif order.adjustment_type == 'line':
				# order.adjustment_scope = 0
				# order.adjustment_section = 0
				# order.adjustment_variable = 0
				# order.adjustment_manuf = 0
				# order.adjustment_sub = 0
				for line in order.material_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal
							
						for scope in order.project_scope_ids:
							prd_scope = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})
						
				for line in order.labour_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})
					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal    
							
						for scope in order.project_scope_ids:
							prd_scope = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

				for line in order.overhead_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal  

						for scope in order.project_scope_ids:
							prd_scope = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})
				
				for line in order.internal_asset_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal

						for scope in order.project_scope_ids:
							prd_scope = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

				for line in order.equipment_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal
						
						for scope in order.project_scope_ids:
							prd_scope = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})
				
				for line in order.subcon_line_ids:
					if line.adjustment_method_line == 'fix':
						line.adjustment_line = line.adjustment_amount_line
						for scope in order.project_scope_ids:
							prd_scope = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})

					else:
						if order.is_set_adjustment_sale == False:
							line.adjustment_line = line.subtotal * (line.adjustment_amount_line / 100)
						else:
							line.adjustment_line = (line.subtotal / (1 - (line.adjustment_amount_line / 100))) - line.subtotal
						
						for scope in order.project_scope_ids:
							prd_scope = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('adjustment_line'))
								scope.sudo().write({'scope_adjustment': adjustment_temp})
						for section in order.section_ids:
							prd_section = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								adjustment_temp = sum(prd_section.mapped('adjustment_line'))
								section.sudo().write({'section_adjustment': adjustment_temp})
						for variable in order.variable_ids:
							prd_variable = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('adjustment_line'))
								variable.sudo().write({'variable_adjustment': adjustment_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								adjustment_temp = sum(prd_manuf.mapped('adjustment_line'))
								manuf.sudo().write({'manuf_adjustment': adjustment_temp})
				
				order.adjustment_sub = sum(order.material_line_ids.mapped('adjustment_line')) + sum(order.labour_line_ids.mapped('adjustment_line')) + sum(order.overhead_line_ids.mapped('adjustment_line')) + sum(order.internal_asset_line_ids.mapped('adjustment_line')) + sum(order.equipment_line_ids.mapped('adjustment_line')) + sum(order.subcon_line_ids.mapped('adjustment_line'))


			elif order.adjustment_type == 'scope':
				# order.adjustment_section = 0
				# order.adjustment_variable = 0
				# order.adjustment_manuf = 0
				# order.adjustment_sub = 0
				# order.line_adjustment = 0
				for scope in order.project_scope_ids:
					if scope.adjustment_method_scope == 'fix':
						scope.scope_adjustment = scope.adjustment_amount_scope
						order.adjustment_sub = sum(order.project_scope_ids.mapped('scope_adjustment'))
						prd_scope1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						number_of_all_lines = len(prd_scope1) + len(prd_scope2) + len(prd_scope3) + len(prd_scope4) + len(prd_scope5) + len(prd_scope6)
						for scope1 in order.material_line_ids:
							if scope1.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope1.sudo().write({'adjustment_line': line_adjustment_line})
						for scope4 in order.labour_line_ids:
							if scope4.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope4.sudo().write({'adjustment_line': line_adjustment_line})
						for scope5 in order.overhead_line_ids:
							if scope5.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope5.sudo().write({'adjustment_line': line_adjustment_line})
						for scope6 in order.internal_asset_line_ids:
							if scope6.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope6.sudo().write({'adjustment_line': line_adjustment_line})
						for scope7 in order.equipment_line_ids:
							if scope7.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope7.sudo().write({'adjustment_line': line_adjustment_line})
						for scope8 in order.subcon_line_ids:
							if scope8.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_all_lines)
								scope8.sudo().write({'adjustment_line': line_adjustment_line})
						for scope2 in order.section_ids:
							prd_scope2 = order.section_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines2 = len(prd_scope2)
							if scope2.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_lines2)
								scope2.sudo().write({'section_adjustment': line_adjustment_line})
						for scope3 in order.variable_ids:
							prd_scope3 = order.variable_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines3 = len(prd_scope3)
							if scope3.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_lines3)
								scope3.sudo().write({'variable_adjustment': line_adjustment_line})
						for scope9 in order.manufacture_line:
							prd_scope9 = order.manufacture_line.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines4 = len(prd_scope9)
							if scope9.project_scope.id == scope.project_scope.id:
								line_adjustment_line = scope.scope_adjustment / float(number_of_lines4)
								scope9.sudo().write({'manuf_adjustment': line_adjustment_line})

					else:
						if order.is_set_adjustment_sale == False:
							scope.scope_adjustment = scope.subtotal_scope * (scope.adjustment_amount_scope / 100)
							order.adjustment_sub = sum(order.project_scope_ids.mapped('scope_adjustment'))
							for scope1 in order.material_line_ids:
								if scope1.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope1.subtotal * (scope.adjustment_amount_scope/100)
									scope1.sudo().write({'adjustment_line': line_adjustment_line})
							for scope4 in order.labour_line_ids:
								if scope4.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope4.subtotal * (scope.adjustment_amount_scope/100)
									scope4.sudo().write({'adjustment_line': line_adjustment_line})
							for scope5 in order.overhead_line_ids:
								if scope5.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope5.subtotal * (scope.adjustment_amount_scope/100)
									scope5.sudo().write({'adjustment_line': line_adjustment_line})
							for scope6 in order.internal_asset_line_ids:
								if scope6.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope6.subtotal * (scope.adjustment_amount_scope/100)
									scope6.sudo().write({'adjustment_line': line_adjustment_line})
							for scope7 in order.equipment_line_ids:
								if scope7.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope7.subtotal * (scope.adjustment_amount_scope/100)
									scope7.sudo().write({'adjustment_line': line_adjustment_line})
							for scope8 in order.subcon_line_ids:
								if scope8.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope8.subtotal * (scope.adjustment_amount_scope/100)
									scope8.sudo().write({'adjustment_line': line_adjustment_line})
							for scope2 in order.section_ids:
								if scope2.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope2.subtotal_section * (scope.adjustment_amount_scope/100)
									scope2.sudo().write({'section_adjustment': line_adjustment_line})
							for scope3 in order.variable_ids:
								if scope3.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope3.subtotal_variable * (scope.adjustment_amount_scope/100)
									scope3.sudo().write({'variable_adjustment': line_adjustment_line})
							for scope9 in order.manufacture_line:
								if scope9.project_scope.id == scope.project_scope.id:
									line_adjustment_line = scope9.subtotal_manuf * (scope.adjustment_amount_scope/100)
									scope9.sudo().write({'manuf_adjustment': line_adjustment_line})
						
						else:
							scope.scope_adjustment = (scope.subtotal_scope / (1 - (scope.adjustment_amount_scope / 100))) - scope.subtotal_scope
							order.adjustment_sub = sum(order.project_scope_ids.mapped('scope_adjustment'))
							for scope1 in order.material_line_ids:
								if scope1.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope1.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope1.subtotal
									scope1.sudo().write({'adjustment_line': line_adjustment_line})
							for scope4 in order.labour_line_ids:
								if scope4.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope4.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope4.subtotal
									scope4.sudo().write({'adjustment_line': line_adjustment_line})
							for scope5 in order.overhead_line_ids:
								if scope5.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope5.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope5.subtotal
									scope5.sudo().write({'adjustment_line': line_adjustment_line})
							for scope6 in order.internal_asset_line_ids:
								if scope6.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope6.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope6.subtotal
									scope6.sudo().write({'adjustment_line': line_adjustment_line})
							for scope7 in order.equipment_line_ids:
								if scope7.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope7.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope7.subtotal
									scope7.sudo().write({'adjustment_line': line_adjustment_line})
							for scope8 in order.subcon_line_ids:
								if scope8.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope8.subtotal / (1 - (scope.adjustment_amount_scope / 100))) - scope8.subtotal
									scope8.sudo().write({'adjustment_line': line_adjustment_line})
							for scope2 in order.section_ids:
								if scope2.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope2.subtotal_section / (1 - (scope.adjustment_amount_scope / 100))) - scope2.subtotal_section
									scope2.sudo().write({'section_adjustment': line_adjustment_line})
							for scope3 in order.variable_ids:
								if scope3.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope3.subtotal_variable / (1 - (scope.adjustment_amount_scope / 100))) - scope3.subtotal_variable
									scope3.sudo().write({'variable_adjustment': line_adjustment_line})
							for scope9 in order.manufacture_line:
								if scope9.project_scope.id == scope.project_scope.id:
									line_adjustment_line = (scope9.subtotal_manuf / (1 - (scope.adjustment_amount_scope / 100))) - scope9.subtotal_manuf
									scope9.sudo().write({'manuf_adjustment': line_adjustment_line})
			
			elif order.adjustment_type == 'section':
				# order.adjustment_scope = 0
				# order.adjustment_variable = 0
				# order.adjustment_manuf = 0
				# order.adjustment_sub = 0
				# order.line_adjustment = 0
				for section in order.section_ids:
					if section.adjustment_method_section == 'fix':
						section.section_adjustment = section.adjustment_amount_section
						order.adjustment_sub = sum(order.section_ids.mapped('section_adjustment'))
						prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)
						
						for section1 in order.material_line_ids:
							if section1.project_scope.id == section.project_scope.id and section1.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section1.sudo().write({'adjustment_line': line_adjustment_line})
						for section4 in order.labour_line_ids:
							if section4.project_scope.id == section.project_scope.id and section4.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section4.sudo().write({'adjustment_line': line_adjustment_line})
						for section5 in order.overhead_line_ids:
							if section5.project_scope.id == section.project_scope.id and section5.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section5.sudo().write({'adjustment_line': line_adjustment_line})
						for section6 in order.internal_asset_line_ids:
							if section6.project_scope.id == section.project_scope.id and section6.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section6.sudo().write({'adjustment_line': line_adjustment_line})
						for section7 in order.equipment_line_ids:
							if section7.project_scope.id == section.project_scope.id and section7.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section7.sudo().write({'adjustment_line': line_adjustment_line})
						for section8 in order.subcon_line_ids:
							if section8.project_scope.id == section.project_scope.id and section8.section_name.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_all_lines)
								section8.sudo().write({'adjustment_line': line_adjustment_line})    
						for section2 in order.project_scope_ids:
							prd_section = order.section_ids.filtered(lambda p: p.project_scope.id == section2.project_scope.id)
							if section2.project_scope.id == section.project_scope.id:
								adjustment_temp = sum(prd_section.mapped('section_adjustment'))
								section2.sudo().write({'scope_adjustment': adjustment_temp})
						for section3 in order.variable_ids:
							prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section.id == section.section.id)
							number_of_lines2 = len(prd_section)
							if section3.project_scope.id == section.project_scope.id and section3.section.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_lines2)
								section3.sudo().write({'variable_adjustment': line_adjustment_line})
						for section9 in order.manufacture_line:
							prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section.id == section.section.id)
							number_of_lines3 = len(prd_section)
							if section9.project_scope.id == section.project_scope.id and section9.section.id == section.section.id:
								line_adjustment_line = section.section_adjustment / float(number_of_lines3)
								section9.sudo().write({'manuf_adjustment': line_adjustment_line})

					else:
						if order.is_set_adjustment_sale == False:
							section.section_adjustment = section.subtotal_section * (section.adjustment_amount_section / 100)
							order.adjustment_sub = sum(order.section_ids.mapped('section_adjustment'))
							for section1 in order.material_line_ids:
								if section1.project_scope.id == section.project_scope.id and section1.section_name.id == section.section.id:
									line_adjustment_line = section1.subtotal * (section.adjustment_amount_section/100)
									section1.sudo().write({'adjustment_line': line_adjustment_line})
							for section4 in order.labour_line_ids:
								if section4.project_scope.id == section.project_scope.id and section4.section_name.id == section.section.id:
									line_adjustment_line = section4.subtotal * (section.adjustment_amount_section/100)
									section4.sudo().write({'adjustment_line': line_adjustment_line})
							for section5 in order.overhead_line_ids:
								if section5.project_scope.id == section.project_scope.id and section5.section_name.id == section.section.id:
									line_adjustment_line = section5.subtotal * (section.adjustment_amount_section/100)
									section5.sudo().write({'adjustment_line': line_adjustment_line})
							for section6 in order.internal_asset_line_ids:
								if section6.project_scope.id == section.project_scope.id and section6.section_name.id == section.section.id:
									line_adjustment_line = section6.subtotal * (section.adjustment_amount_section/100)
									section6.sudo().write({'adjustment_line': line_adjustment_line})
							for section7 in order.equipment_line_ids:
								if section7.project_scope.id == section.project_scope.id and section7.section_name.id == section.section.id:
									line_adjustment_line = section7.subtotal * (section.adjustment_amount_section/100)
									section7.sudo().write({'adjustment_line': line_adjustment_line})
							for section8 in order.subcon_line_ids:
								if section8.project_scope.id == section.project_scope.id and section8.section_name.id == section.section.id:
									line_adjustment_line = section8.subtotal * (section.adjustment_amount_section/100)
									section8.sudo().write({'adjustment_line': line_adjustment_line})
							for section2 in order.project_scope_ids:
								prd_section = order.section_ids.filtered(lambda p: p.project_scope.id == section2.project_scope.id)
								if section2.project_scope.id == section.project_scope.id:
									adjustment_temp = sum(prd_section.mapped('section_adjustment'))
									section2.sudo().write({'scope_adjustment': adjustment_temp})
							for section3 in order.variable_ids:
								if section3.project_scope.id == section.project_scope.id and section3.section.id == section.section.id:
									line_adjustment_line = section3.subtotal_variable * (section.adjustment_amount_section/100)
									section3.sudo().write({'variable_adjustment': line_adjustment_line})
							for section9 in order.manufacture_line:
								if section9.project_scope.id == section.project_scope.id and section9.section.id == section.section.id:
									line_adjustment_line = section9.subtotal_manuf * (section.adjustment_amount_section/100)
									section9.sudo().write({'manuf_adjustment': line_adjustment_line})
						
						else:
							section.section_adjustment = (section.subtotal_section / (1 - (section.adjustment_amount_section / 100))) - section.subtotal_section
							order.adjustment_sub = sum(order.section_ids.mapped('section_adjustment'))
							for section1 in order.material_line_ids:
								if section1.project_scope.id == section.project_scope.id and section1.section_name.id == section.section.id:
									line_adjustment_line = (section1.subtotal / (1 - (section.adjustment_amount_section / 100))) - section1.subtotal
									section1.sudo().write({'adjustment_line': line_adjustment_line})
							for section4 in order.labour_line_ids:
								if section4.project_scope.id == section.project_scope.id and section4.section_name.id == section.section.id:
									line_adjustment_line = (section4.subtotal / (1 - (section.adjustment_amount_section / 100))) - section4.subtotal
									section4.sudo().write({'adjustment_line': line_adjustment_line})
							for section5 in order.overhead_line_ids:
								if section5.project_scope.id == section.project_scope.id and section5.section_name.id == section.section.id:
									line_adjustment_line = (section5.subtotal / (1 - (section.adjustment_amount_section / 100))) - section5.subtotal
									section5.sudo().write({'adjustment_line': line_adjustment_line})
							for section6 in order.internal_asset_line_ids:
								if section6.project_scope.id == section.project_scope.id and section6.section_name.id == section.section.id:
									line_adjustment_line = (section6.subtotal / (1 - (section.adjustment_amount_section / 100))) - section6.subtotal
									section6.sudo().write({'adjustment_line': line_adjustment_line})
							for section7 in order.equipment_line_ids:
								if section7.project_scope.id == section.project_scope.id and section7.section_name.id == section.section.id:
									line_adjustment_line = (section7.subtotal / (1 - (section.adjustment_amount_section / 100))) - section7.subtotal
									section7.sudo().write({'adjustment_line': line_adjustment_line})
							for section8 in order.subcon_line_ids:
								if section8.project_scope.id == section.project_scope.id and section8.section_name.id == section.section.id:
									line_adjustment_line = (section8.subtotal / (1 - (section.adjustment_amount_section / 100))) - section8.subtotal
									section8.sudo().write({'adjustment_line': line_adjustment_line})
							for section2 in order.project_scope_ids:
								prd_section = order.section_ids.filtered(lambda p: p.project_scope.id == section2.project_scope.id)
								if section2.project_scope.id == section.project_scope.id:
									adjustment_temp = sum(prd_section.mapped('section_adjustment'))
									section2.sudo().write({'scope_adjustment': adjustment_temp})
							for section3 in order.variable_ids:
								if section3.project_scope.id == section.project_scope.id and section3.section.id == section.section.id:
									line_adjustment_line = (section3.subtotal_variable / (1 - (section.adjustment_amount_section / 100))) - section3.subtotal_variable
									section3.sudo().write({'variable_adjustment': line_adjustment_line})
							for section9 in order.manufacture_line:
								if section9.project_scope.id == section.project_scope.id and section9.section.id == section.section.id:
									line_adjustment_line = (section9.subtotal_manuf / (1 - (section.adjustment_amount_section / 100))) - section9.subtotal_manuf
									section9.sudo().write({'manuf_adjustment': line_adjustment_line})

			# elif order.adjustment_type == 'variable':
			# 	# order.adjustment_scope = 0
			# 	# order.adjustment_section = 0
			# 	# order.adjustment_manuf = 0
			# 	# order.adjustment_sub = 0
			# 	# order.line_adjustment = 0
			# 	for variable in order.variable_ids:
			# 		if variable.adjustment_method_variable == 'fix':
			# 			variable.variable_adjustment = variable.adjustment_amount_variable
			# 			order.adjustment_sub = sum(order.variable_ids.mapped('variable_adjustment'))
			# 			prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)
			#
			# 			for variable1 in order.material_line_ids:
			# 				if variable1.project_scope.id == variable.project_scope.id and variable1.section_name.id == variable.section.id and variable1.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable1.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable4 in order.labour_line_ids:
			# 				if variable4.project_scope.id == variable.project_scope.id and variable4.section_name.id == variable.section.id and variable4.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable4.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable5 in order.overhead_line_ids:
			# 				if variable5.project_scope.id == variable.project_scope.id and variable5.section_name.id == variable.section.id and variable5.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable5.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable6 in order.internal_asset_line_ids:
			# 				if variable6.project_scope.id == variable.project_scope.id and variable6.section_name.id == variable.section.id and variable6.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable6.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable7 in order.equipment_line_ids:
			# 				if variable7.project_scope.id == variable.project_scope.id and variable7.section_name.id == variable.section.id and variable7.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable7.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable8 in order.subcon_line_ids:
			# 				if variable8.project_scope.id == variable.project_scope.id and variable8.section_name.id == variable.section.id and variable8.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_all_lines)
			# 					variable8.sudo().write({'adjustment_line': line_adjustment_line})
			# 			for variable2 in order.project_scope_ids:
			# 				prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == variable2.project_scope.id)
			# 				if variable2.project_scope.id == variable.project_scope.id:
			# 					adjustment_temp = sum(prd_scope.mapped('variable_adjustment'))
			# 					variable2.sudo().write({'scope_adjustment': adjustment_temp})
			# 			for variable3 in order.section_ids:
			# 				prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == variable3.project_scope.id and p.section.id == variable3.section.id)
			# 				if variable3.project_scope.id == variable.project_scope.id and variable3.section.id == variable.section.id:
			# 					adjustment_temp = sum(prd_section.mapped('variable_adjustment'))
			# 					variable3.sudo().write({'section_adjustment': adjustment_temp})
			# 			for variable9 in order.manufacture_line:
			# 				prd_manuf = order.manufacture_line.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 				number_of_lines1 = len(prd_manuf)
			# 				if variable9.project_scope.id == variable.project_scope.id and variable9.section.id == variable.section.id and variable9.variable_ref.id == variable.variable.id:
			# 					line_adjustment_line = variable.variable_adjustment / float(number_of_lines1)
			# 					variable9.sudo().write({'manuf_adjustment': line_adjustment_line})
			#
			# 		else:
			# 			if order.is_set_adjustment_sale == False:
			# 				variable.variable_adjustment = variable.subtotal_variable * (variable.adjustment_amount_variable / 100)
			# 				order.adjustment_sub = sum(order.variable_ids.mapped('variable_adjustment'))
			# 				for variable1 in order.material_line_ids:
			# 					if variable1.project_scope.id == variable.project_scope.id and variable1.section_name.id == variable.section.id and variable1.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable1.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable1.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable4 in order.labour_line_ids:
			# 					if variable4.project_scope.id == variable.project_scope.id and variable4.section_name.id == variable.section.id and variable4.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable4.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable4.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable5 in order.overhead_line_ids:
			# 					if variable5.project_scope.id == variable.project_scope.id and variable5.section_name.id == variable.section.id and variable5.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable5.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable5.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable6 in order.internal_asset_line_ids:
			# 					if variable6.project_scope.id == variable.project_scope.id and variable6.section_name.id == variable.section.id and variable6.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable6.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable6.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable7 in order.equipment_line_ids:
			# 					if variable7.project_scope.id == variable.project_scope.id and variable7.section_name.id == variable.section.id and variable7.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable7.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable7.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable8 in order.subcon_line_ids:
			# 					if variable8.project_scope.id == variable.project_scope.id and variable8.section_name.id == variable.section.id and variable8.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable8.subtotal * (variable.adjustment_amount_variable/100)
			# 						variable8.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable2 in order.project_scope_ids:
			# 					prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == variable2.project_scope.id)
			# 					if variable2.project_scope.id == variable.project_scope.id:
			# 						adjustment_temp = sum(prd_scope.mapped('variable_adjustment'))
			# 						variable2.sudo().write({'scope_adjustment': adjustment_temp})
			# 				for variable3 in order.section_ids:
			# 					prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == variable3.project_scope.id and p.section.id == variable3.section.id)
			# 					if variable3.project_scope.id == variable.project_scope.id and variable3.section.id == variable.section.id:
			# 						adjustment_temp = sum(prd_section.mapped('variable_adjustment'))
			# 						variable3.sudo().write({'section_adjustment': adjustment_temp})
			# 				for variable9 in order.manufacture_line:
			# 					if variable9.project_scope.id == variable.project_scope.id and variable9.section.id == variable.section.id and variable9.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = variable9.subtotal_manuf * (variable.adjustment_amount_variable/100)
			# 						variable9.sudo().write({'manuf_adjustment': line_adjustment_line})
			#
			# 			else:
			# 				variable.variable_adjustment = (variable.subtotal_variable / (1 - (variable.adjustment_amount_variable / 100))) - variable.subtotal_variable
			# 				order.adjustment_sub = sum(order.variable_ids.mapped('variable_adjustment'))
			# 				for variable1 in order.material_line_ids:
			# 					if variable1.project_scope.id == variable.project_scope.id and variable1.section_name.id == variable.section.id and variable1.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable1.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable1.subtotal
			# 						variable1.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable4 in order.labour_line_ids:
			# 					if variable4.project_scope.id == variable.project_scope.id and variable4.section_name.id == variable.section.id and variable4.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable4.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable4.subtotal
			# 						variable4.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable5 in order.overhead_line_ids:
			# 					if variable5.project_scope.id == variable.project_scope.id and variable5.section_name.id == variable.section.id and variable5.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable5.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable5.subtotal
			# 						variable5.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable6 in order.internal_asset_line_ids:
			# 					if variable6.project_scope.id == variable.project_scope.id and variable6.section_name.id == variable.section.id and variable6.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable6.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable6.subtotal
			# 						variable6.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable7 in order.equipment_line_ids:
			# 					if variable7.project_scope.id == variable.project_scope.id and variable7.section_name.id == variable.section.id and variable7.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable7.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable7.subtotal
			# 						variable7.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable8 in order.subcon_line_ids:
			# 					if variable8.project_scope.id == variable.project_scope.id and variable8.section_name.id == variable.section.id and variable8.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable8.subtotal / (1 - (variable.adjustment_amount_variable / 100))) - variable8.subtotal
			# 						variable8.sudo().write({'adjustment_line': line_adjustment_line})
			# 				for variable2 in order.project_scope_ids:
			# 					prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == variable2.project_scope.id)
			# 					if variable2.project_scope.id == variable.project_scope.id:
			# 						adjustment_temp = sum(prd_scope.mapped('variable_adjustment'))
			# 						variable2.sudo().write({'scope_adjustment': adjustment_temp})
			# 				for variable3 in order.section_ids:
			# 					prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == variable3.project_scope.id and p.section.id == variable3.section.id)
			# 					if variable3.project_scope.id == variable.project_scope.id and variable3.section.id == variable.section.id:
			# 						adjustment_temp = sum(prd_section.mapped('variable_adjustment'))
			# 						variable3.sudo().write({'section_adjustment': adjustment_temp})
			# 				for variable9 in order.manufacture_line:
			# 					if variable9.project_scope.id == variable.project_scope.id and variable9.section.id == variable.section.id and variable9.variable_ref.id == variable.variable.id:
			# 						line_adjustment_line = (variable9.subtotal_manuf / (1 - (variable.adjustment_amount_variable / 100))) - variable9.subtotal_manuf
			# 						variable9.sudo().write({'manuf_adjustment': line_adjustment_line})
			
			elif order.adjustment_type == 'manuf':
				# order.adjustment_scope = 0
				# order.adjustment_section = 0
				# order.adjustment_variable = 0
				# order.adjustment_sub = 0
				# order.line_adjustment = 0
				for manuf in order.manufacture_line:
					if manuf.adjustment_method_manuf == 'fix':
						manuf.manuf_adjustment = manuf.adjustment_amount_manuf
						order.adjustment_sub = sum(order.manufacture_line.mapped('manuf_adjustment'))
						prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)

						for manuf1 in order.material_line_ids:
							if manuf1.project_scope.id == manuf.project_scope.id and manuf1.section_name.id == manuf.section.id and manuf1.variable_ref.id == manuf.variable_ref.id and manuf1.finish_good_id.id == manuf.finish_good_id.id and manuf1.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf1.sudo().write({'adjustment_line': line_adjustment_line})
						for manuf2 in order.labour_line_ids:
							if manuf2.project_scope.id == manuf.project_scope.id and manuf2.section_name.id == manuf.section.id and manuf2.variable_ref.id == manuf.variable_ref.id and manuf2.finish_good_id.id == manuf.finish_good_id.id and manuf2.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf2.sudo().write({'adjustment_line': line_adjustment_line})
						for manuf3 in order.overhead_line_ids:
							if manuf3.project_scope.id == manuf.project_scope.id and manuf3.section_name.id == manuf.section.id and manuf3.variable_ref.id == manuf.variable_ref.id and manuf3.finish_good_id.id == manuf.finish_good_id.id and manuf3.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf3.sudo().write({'adjustment_line': line_adjustment_line})
						for manuf4 in order.internal_asset_line_ids:
							if manuf4.project_scope.id == manuf.project_scope.id and manuf4.section_name.id == manuf.section.id and manuf4.variable_ref.id == manuf.variable_ref.id and manuf4.finish_good_id.id == manuf.finish_good_id.id and manuf4.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf4.sudo().write({'adjustment_line': line_adjustment_line})
						for manuf5 in order.equipment_line_ids:
							if manuf5.project_scope.id == manuf.project_scope.id and manuf5.section_name.id == manuf.section.id and manuf5.variable_ref.id == manuf.variable_ref.id and manuf5.finish_good_id.id == manuf.finish_good_id.id and manuf5.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf5.sudo().write({'adjustment_line': line_adjustment_line})
						for manuf6 in order.subcon_line_ids:
							if manuf6.project_scope.id == manuf.project_scope.id and manuf6.section_name.id == manuf.section.id and manuf6.variable_ref.id == manuf.variable_ref.id and manuf6.finish_good_id.id == manuf.finish_good_id.id and manuf6.bom_id.id == manuf.bom_id.id:
								line_adjustment_line = manuf.manuf_adjustment / float(number_of_all_lines)
								manuf6.sudo().write({'adjustment_line': line_adjustment_line})   
						for manuf7 in order.project_scope_ids:
							prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf7.project_scope.id)
							if manuf7.project_scope.id == manuf.project_scope.id:
								adjustment_temp = sum(prd_scope.mapped('manuf_adjustment'))
								manuf7.sudo().write({'scope_adjustment': adjustment_temp})
						for manuf8 in order.section_ids:
							prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf8.project_scope.id and p.section.id == manuf8.section.id)
							if manuf8.project_scope.id == manuf.project_scope.id and manuf8.section.id == manuf.section.id:
								adjustment_temp = sum(prd_section.mapped('manuf_adjustment'))
								manuf8.sudo().write({'section_adjustment': adjustment_temp})
						for manuf9 in order.variable_ids:
							prd_variable = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf9.project_scope.id and p.section.id == manuf9.section.id and p.variable_ref.id == manuf9.variable.id)
							if manuf9.project_scope.id == manuf.project_scope.id and manuf9.section.id == manuf.section.id and manuf9.variable.id == manuf.variable_ref.id:
								adjustment_temp = sum(prd_variable.mapped('manuf_adjustment'))
								manuf9.sudo().write({'variable_adjustment': adjustment_temp})
						
					else:
						if order.is_set_adjustment_sale == False:
							manuf.manuf_adjustment = manuf.subtotal_manuf * (manuf.adjustment_amount_manuf / 100)
							order.adjustment_sub = sum(order.manufacture_line.mapped('manuf_adjustment'))
							for manuf1 in order.material_line_ids:
								if manuf1.project_scope.id == manuf.project_scope.id and manuf1.section_name.id == manuf.section.id and manuf1.variable_ref.id == manuf.variable_ref.id and manuf1.finish_good_id.id == manuf.finish_good_id.id and manuf1.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf1.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf1.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf2 in order.labour_line_ids:
								if manuf2.project_scope.id == manuf.project_scope.id and manuf2.section_name.id == manuf.section.id and manuf2.variable_ref.id == manuf.variable_ref.id and manuf2.finish_good_id.id == manuf.finish_good_id.id and manuf2.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf2.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf2.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf3 in order.overhead_line_ids:
								if manuf3.project_scope.id == manuf.project_scope.id and manuf3.section_name.id == manuf.section.id and manuf3.variable_ref.id == manuf.variable_ref.id and manuf3.finish_good_id.id == manuf.finish_good_id.id and manuf3.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf3.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf3.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf4 in order.internal_asset_line_ids:
								if manuf4.project_scope.id == manuf.project_scope.id and manuf4.section_name.id == manuf.section.id and manuf4.variable_ref.id == manuf.variable_ref.id and manuf4.finish_good_id.id == manuf.finish_good_id.id and manuf4.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf4.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf4.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf5 in order.equipment_line_ids:
								if manuf5.project_scope.id == manuf.project_scope.id and manuf5.section_name.id == manuf.section.id and manuf5.variable_ref.id == manuf.variable_ref.id and manuf5.finish_good_id.id == manuf.finish_good_id.id and manuf5.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf5.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf5.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf6 in order.subcon_line_ids:
								if manuf6.project_scope.id == manuf.project_scope.id and manuf6.section_name.id == manuf.section.id and manuf6.variable_ref.id == manuf.variable_ref.id and manuf6.finish_good_id.id == manuf.finish_good_id.id and manuf6.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = manuf6.subtotal * (manuf.adjustment_amount_manuf/100)
									manuf6.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf7 in order.project_scope_ids:
								prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf7.project_scope.id)
								if manuf7.project_scope.id == manuf.project_scope.id:
									adjustment_temp = sum(prd_scope.mapped('manuf_adjustment'))
									manuf7.sudo().write({'scope_adjustment': adjustment_temp})
							for manuf8 in order.section_ids:
								prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf8.project_scope.id and p.section.id == manuf8.section.id)
								if manuf8.project_scope.id == manuf.project_scope.id and manuf8.section.id == manuf.section.id:
									adjustment_temp = sum(prd_section.mapped('manuf_adjustment'))
									manuf8.sudo().write({'section_adjustment': adjustment_temp})
							for manuf9 in order.variable_ids:
								prd_variable = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf9.project_scope.id and p.section.id == manuf9.section.id and p.variable_ref.id == manuf9.variable.id)
								if manuf9.project_scope.id == manuf.project_scope.id and manuf9.section.id == manuf.section.id and manuf9.variable.id == manuf.variable_ref.id:
									adjustment_temp = sum(prd_variable.mapped('manuf_adjustment'))
									manuf9.sudo().write({'variable_adjustment': adjustment_temp})
						
						else:
							manuf.manuf_adjustment = (manuf.subtotal_manuf / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf.subtotal_manuf
							order.adjustment_sub = sum(order.manufacture_line.mapped('manuf_adjustment'))
							for manuf1 in order.material_line_ids:
								if manuf1.project_scope.id == manuf.project_scope.id and manuf1.section_name.id == manuf.section.id and manuf1.variable_ref.id == manuf.variable_ref.id and manuf1.finish_good_id.id == manuf.finish_good_id.id and manuf1.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf1.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf1.subtotal
									manuf1.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf2 in order.labour_line_ids:
								if manuf2.project_scope.id == manuf.project_scope.id and manuf2.section_name.id == manuf.section.id and manuf2.variable_ref.id == manuf.variable_ref.id and manuf2.finish_good_id.id == manuf.finish_good_id.id and manuf2.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf2.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf2.subtotal
									manuf2.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf3 in order.overhead_line_ids:
								if manuf3.project_scope.id == manuf.project_scope.id and manuf3.section_name.id == manuf.section.id and manuf3.variable_ref.id == manuf.variable_ref.id and manuf3.finish_good_id.id == manuf.finish_good_id.id and manuf3.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf3.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf3.subtotal
									manuf3.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf4 in order.internal_asset_line_ids:
								if manuf4.project_scope.id == manuf.project_scope.id and manuf4.section_name.id == manuf.section.id and manuf4.variable_ref.id == manuf.variable_ref.id and manuf4.finish_good_id.id == manuf.finish_good_id.id and manuf4.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf4.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf4.subtotal
									manuf4.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf5 in order.equipment_line_ids:
								if manuf5.project_scope.id == manuf.project_scope.id and manuf5.section_name.id == manuf.section.id and manuf5.variable_ref.id == manuf.variable_ref.id and manuf5.finish_good_id.id == manuf.finish_good_id.id and manuf5.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf5.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf5.subtotal
									manuf5.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf6 in order.subcon_line_ids:
								if manuf6.project_scope.id == manuf.project_scope.id and manuf6.section_name.id == manuf.section.id and manuf6.variable_ref.id == manuf.variable_ref.id and manuf6.finish_good_id.id == manuf.finish_good_id.id and manuf6.bom_id.id == manuf.bom_id.id:
									line_adjustment_line = (manuf6.subtotal / (1 - (manuf.adjustment_amount_manuf / 100))) - manuf6.subtotal
									manuf6.sudo().write({'adjustment_line': line_adjustment_line})
							for manuf7 in order.project_scope_ids:
								prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf7.project_scope.id)
								if manuf7.project_scope.id == manuf.project_scope.id:
									adjustment_temp = sum(prd_scope.mapped('manuf_adjustment'))
									manuf7.sudo().write({'scope_adjustment': adjustment_temp})
							for manuf8 in order.section_ids:
								prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf8.project_scope.id and p.section.id == manuf8.section.id)
								if manuf8.project_scope.id == manuf.project_scope.id and manuf8.section.id == manuf.section.id:
									adjustment_temp = sum(prd_section.mapped('manuf_adjustment'))
									manuf8.sudo().write({'section_adjustment': adjustment_temp})
							for manuf9 in order.variable_ids:
								prd_variable = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf9.project_scope.id and p.section.id == manuf9.section.id and p.variable_ref.id == manuf9.variable.id)
								if manuf9.project_scope.id == manuf.project_scope.id and manuf9.section.id == manuf.section.id and manuf9.variable.id == manuf.variable_ref.id:
									adjustment_temp = sum(prd_variable.mapped('manuf_adjustment'))
									manuf9.sudo().write({'variable_adjustment': adjustment_temp})
			
			else:
				# order.adjustment_scope = 0
				# order.adjustment_section = 0
				# order.adjustment_variable = 0
				# order.adjustment_manuf = 0
				order.adjustment_sub = 0
				# order.line_adjustment = 0

			if order.discount_type == 'global':
				# order.discount_scope = 0
				# order.discount_section = 0
				# order.discount_variable = 0
				# order.discount_manuf = 0
				# order.line_discount = 0
				if order.discount_method_global == 'fix':
					order.discount_sub = order.discount_amount_global
					number_of_all_lines = len(order.material_line_ids) + len(order.labour_line_ids) + len(order.overhead_line_ids) + len(order.internal_asset_line_ids) + len(order.equipment_line_ids) + len(order.subcon_line_ids)
					number_of_lines_scope = len(order.project_scope_ids)
					number_of_lines_section = len(order.section_ids)
					number_of_lines_variable = len(order.variable_ids)
					number_of_lines_manuf = len(order.manufacture_line)
					for line1 in order.material_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line1.sudo().write({'discount_line': line_discount_line})
					for line2 in order.labour_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line2.sudo().write({'discount_line': line_discount_line})
					for line3 in order.overhead_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line3.sudo().write({'discount_line': line_discount_line})
					for line4 in order.internal_asset_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line4.sudo().write({'discount_line': line_discount_line})
					for line5 in order.equipment_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line5.sudo().write({'discount_line': line_discount_line})
					for line6 in order.subcon_line_ids:
						line_discount_line = order.discount_amount_global / number_of_all_lines
						line6.sudo().write({'discount_line': line_discount_line})
					for scope in order.project_scope_ids:
						line_discount_scope = order.discount_amount_global / number_of_lines_scope
						scope.sudo().write({'scope_discount': line_discount_scope})
					for section in order.section_ids:
						line_discount_section = order.discount_amount_global / number_of_lines_section
						section.sudo().write({'section_discount': line_discount_section})
					for variable in order.variable_ids:
						line_discount_variable = order.discount_amount_global / number_of_lines_variable
						variable.sudo().write({'variable_discount': line_discount_variable})
					for manuf in order.manufacture_line:
						line_discount_manuf = order.discount_amount_global / number_of_lines_manuf
						manuf.sudo().write({'manuf_discount': line_discount_manuf})

				else:
					order.discount_sub = (order.amount_untaxed + order.adjustment_scope + order.adjustment_section + order.adjustment_sub + order.line_adjustment) * (order.discount_amount_global / 100)
					for line1 in order.material_line_ids:
						line_discount_line = (line1.subtotal + line1.adjustment_line) * (order.discount_amount_global/100)
						line1.sudo().write({'discount_line': line_discount_line})
					for line2 in order.labour_line_ids:
						line_discount_line = (line2.subtotal + line2.adjustment_line) * (order.discount_amount_global/100)
						line2.sudo().write({'discount_line': line_discount_line})
					for line3 in order.overhead_line_ids:
						line_discount_line = (line3.subtotal + line3.adjustment_line) * (order.discount_amount_global/100)
						line3.sudo().write({'discount_line': line_discount_line})
					for line4 in order.internal_asset_line_ids:
						line_discount_line = (line4.subtotal + line4.adjustment_line) * (order.discount_amount_global/100)
						line4.sudo().write({'discount_line': line_discount_line})
					for line5 in order.equipment_line_ids:
						line_discount_line = (line5.subtotal + line5.adjustment_line) * (order.discount_amount_global/100)
						line5.sudo().write({'discount_line': line_discount_line})
					for line6 in order.subcon_line_ids:
						line_discount_line = (line6.subtotal + line6.adjustment_line) * (order.discount_amount_global/100)
						line6.sudo().write({'discount_line': line_discount_line})
					for scope in order.project_scope_ids:
						line_discount_scope = (scope.subtotal_scope + scope.scope_adjustment) * (order.discount_amount_global/100)
						scope.sudo().write({'scope_discount': line_discount_scope})
					for section in order.section_ids:
						line_discount_section = (section.subtotal_section + section.section_adjustment) * (order.discount_amount_global/100)
						section.sudo().write({'section_discount': line_discount_section})
					for variable in order.variable_ids:
						line_discount_variable = (variable.subtotal_variable + variable.variable_adjustment) * (order.discount_amount_global/100)
						variable.sudo().write({'variable_discount': line_discount_variable})
					for manuf in order.manufacture_line:
						line_discount_manuf = (manuf.subtotal_manuf + manuf.manuf_adjustment) * (order.discount_amount_global/100)
						manuf.sudo().write({'manuf_discount': line_discount_manuf})
				
			elif order.discount_type == 'line':
				# order.discount_scope = 0
				# order.discount_section = 0
				# order.discount_variable = 0
				# order.discount_manuf = 0
				# order.discount_sub = 0
				for line in order.material_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})
				
				for line in order.labour_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

				for line in order.overhead_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.section.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

				for line in order.internal_asset_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.section.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

				for line in order.equipment_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.section.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})
				
				for line in order.subcon_line_ids:
					if line.discount_method_line == 'fix':
						line.discount_line = line.discount_amount_line  
						for scope in order.project_scope_ids:
							prd_scope = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.section.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

					else:
						line.discount_line = (line.subtotal + line.adjustment_line) * (line.discount_amount_line / 100)
						for scope in order.project_scope_ids:
							prd_scope = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							if scope.project_scope.id == line.project_scope.id:
								discount_temp = sum(prd_scope.mapped('discount_line'))
								scope.sudo().write({'scope_discount': discount_temp})
						for section in order.section_ids:
							prd_section = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
							if section.project_scope.id == line.project_scope.id and section.section.id == line.section_name.id:
								discount_temp = sum(prd_section.mapped('discount_line'))
								section.sudo().write({'section_discount': discount_temp})
						for variable in order.variable_ids:
							prd_variable = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
							if variable.project_scope.id == line.project_scope.id and variable.section.id == line.section_name.id and variable.variable.id == line.variable_ref.id:
								discount_temp = sum(prd_variable.mapped('discount_line'))
								variable.sudo().write({'variable_discount': discount_temp})
						for manuf in order.manufacture_line:
							prd_manuf = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
							if manuf.project_scope.id == line.project_scope.id and manuf.section.id == line.section_name.id and manuf.variable_ref.id == line.variable_ref.id and manuf.finish_good_id.id == line.finish_good_id.id and manuf.bom_id.id == line.bom_id.id:
								discount_temp = sum(prd_manuf.mapped('discount_line'))
								manuf.sudo().write({'manuf_discount': discount_temp})

				order.discount_sub = sum(order.material_line_ids.mapped('discount_line')) + sum(order.labour_line_ids.mapped('discount_line')) + sum(order.overhead_line_ids.mapped('discount_line')) + sum(order.internal_asset_line_ids.mapped('discount_line')) + sum(order.equipment_line_ids.mapped('discount_line')) + sum(order.subcon_line_ids.mapped('discount_line'))

			elif order.discount_type == 'scope':
				# order.discount_section = 0
				# order.discount_variable = 0
				# order.discount_manuf = 0
				# order.discount_sub = 0
				# order.line_discount = 0
				for scope in order.project_scope_ids:
					if scope.discount_method_scope == 'fix':
						scope.scope_discount = scope.discount_amount_scope
						order.discount_sub = sum(order.project_scope_ids.mapped('scope_discount'))
						prd_scope1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						prd_scope6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
						number_of_all_lines = len(prd_scope1) + len(prd_scope2) + len(prd_scope3) + len(prd_scope4) + len(prd_scope5) + len(prd_scope6)
						for scope1 in order.material_line_ids:
							if scope1.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope1.sudo().write({'discount_line': line_discount_line})
						for scope4 in order.labour_line_ids:
							if scope4.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope4.sudo().write({'discount_line': line_discount_line})
						for scope5 in order.overhead_line_ids:
							if scope5.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope5.sudo().write({'discount_line': line_discount_line})
						for scope6 in order.internal_asset_line_ids:
							if scope6.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope6.sudo().write({'discount_line': line_discount_line})
						for scope7 in order.equipment_line_ids:
							if scope7.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope7.sudo().write({'discount_line': line_discount_line})
						for scope8 in order.subcon_line_ids:
							if scope8.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_all_lines)
								scope8.sudo().write({'discount_line': line_discount_line})
						for scope2 in order.section_ids:
							prd_scope = order.section_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines = len(prd_scope)
							if scope2.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_lines)
								scope2.sudo().write({'section_discount': line_discount_line})
						for scope3 in order.variable_ids:
							prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines = len(prd_scope)
							if scope3.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_lines)
								scope3.sudo().write({'variable_discount': line_discount_line})
						for scope9 in order.manufacture_line:
							prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == scope.project_scope.id)
							number_of_lines = len(prd_scope)
							if scope9.project_scope.id == scope.project_scope.id:
								line_discount_line = scope.scope_discount / float(number_of_lines)
								scope9.sudo().write({'manuf_discount': line_discount_line})
					
					else:
						scope.scope_discount = (scope.subtotal_scope + scope.scope_adjustment) * (scope.discount_amount_scope / 100)
						order.discount_sub = sum(order.project_scope_ids.mapped('scope_discount'))
						for scope1 in order.material_line_ids:
							if scope1.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope1.subtotal + scope1.adjustment_line) * (scope.discount_amount_scope/100)
								scope1.sudo().write({'discount_line': line_discount_line})
						for scope4 in order.labour_line_ids:
							if scope4.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope4.subtotal + scope4.adjustment_line) * (scope.discount_amount_scope/100)
								scope4.sudo().write({'discount_line': line_discount_line})
						for scope5 in order.overhead_line_ids:
							if scope5.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope5.subtotal + scope5.adjustment_line) * (scope.discount_amount_scope/100)
								scope5.sudo().write({'discount_line': line_discount_line})
						for scope6 in order.internal_asset_line_ids:
							if scope6.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope6.subtotal + scope6.adjustment_line) * (scope.discount_amount_scope/100)
								scope6.sudo().write({'discount_line': line_discount_line})
						for scope7 in order.equipment_line_ids:
							if scope7.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope7.subtotal + scope7.adjustment_line) * (scope.discount_amount_scope/100)
								scope7.sudo().write({'discount_line': line_discount_line})
						for scope8 in order.subcon_line_ids:
							if scope8.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope8.subtotal + scope8.adjustment_line) * (scope.discount_amount_scope/100)
								scope8.sudo().write({'discount_line': line_discount_line})
						for scope2 in order.section_ids:
							if scope2.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope2.subtotal_section + scope2.section_adjustment) * (scope.discount_amount_scope/100)
								scope2.sudo().write({'section_discount': line_discount_line})
						for scope3 in order.variable_ids:
							if scope3.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope3.subtotal_variable + scope3.variable_adjustment) * (scope.discount_amount_scope/100)
								scope3.sudo().write({'variable_discount': line_discount_line})
						for scope9 in order.manufacture_line:
							if scope9.project_scope.id == scope.project_scope.id:
								line_discount_line = (scope9.subtotal_manuf + scope9.manuf_adjustment) * (scope.discount_amount_scope/100)
								scope9.sudo().write({'manuf_discount': line_discount_line})
					
			elif order.discount_type == 'section':
				# order.discount_scope = 0
				# order.discount_variable = 0
				# order.discount_manuf = 0
				# order.discount_sub = 0
				# order.line_discount = 0
				for section in order.section_ids:
					if section.discount_method_section == 'fix':
						section.section_discount = section.discount_amount_section
						order.discount_sub = sum(order.section_ids.mapped('section_discount'))
						prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section_name.id == section.section.id)
						number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)
						for section1 in order.material_line_ids:
							if section1.project_scope.id == section.project_scope.id and section1.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section1.sudo().write({'discount_line': line_discount_line})
						for section4 in order.labour_line_ids:
							if section4.project_scope.id == section.project_scope.id and section4.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section4.sudo().write({'discount_line': line_discount_line})
						for section5 in order.overhead_line_ids:
							if section5.project_scope.id == section.project_scope.id and section5.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section5.sudo().write({'discount_line': line_discount_line})
						for section6 in order.internal_asset_line_ids:
							if section6.project_scope.id == section.project_scope.id and section6.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section6.sudo().write({'discount_line': line_discount_line})
						for section7 in order.equipment_line_ids:
							if section7.project_scope.id == section.project_scope.id and section7.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section7.sudo().write({'discount_line': line_discount_line})
						for section8 in order.subcon_line_ids:
							if section8.project_scope.id == section.project_scope.id and section8.section_name.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_all_lines)
								section8.sudo().write({'discount_line': line_discount_line})
						for section2 in order.project_scope_ids:
							prd_section = order.section_ids.filtered(lambda p: p.project_scope.id == section2.project_scope.id)
							if section2.project_scope.id == section.project_scope.id:
								line_discount_line = sum(prd_section.mapped('section_discount'))
								section2.sudo().write({'scope_discount': line_discount_line})
						for section3 in order.variable_ids:
							prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == section.project_scope.id and p.section.id == section.section.id)
							number_of_lines = len(prd_section)
							if section3.project_scope.id == section.project_scope.id and section3.section.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_lines)
								section3.sudo().write({'variable_discount': line_discount_line})
						for section9 in order.manufacture_line:
							prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == section9.project_scope.id and p.section.id == section9.section.id)
							number_of_lines = len(prd_section)
							if section9.project_scope.id == section.project_scope.id and section9.section.id == section.section.id:
								line_discount_line = section.section_discount / float(number_of_lines)
								section9.sudo().write({'manuf_discount': line_discount_line})

					else:
						section.section_discount = (section.subtotal_section + section.section_adjustment) * (section.discount_amount_section / 100)
						order.discount_sub = sum(order.section_ids.mapped('section_discount'))
						for section1 in order.material_line_ids:
							if section1.project_scope.id == section.project_scope.id and section1.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section1.sudo().write({'discount_line': line_discount_line})
						for section4 in order.labour_line_ids:
							if section4.project_scope.id == section.project_scope.id and section4.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section4.sudo().write({'discount_line': line_discount_line})
						for section5 in order.overhead_line_ids:
							if section5.project_scope.id == section.project_scope.id and section5.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section5.sudo().write({'discount_line': line_discount_line})
						for section6 in order.internal_asset_line_ids:
							if section6.project_scope.id == section.project_scope.id and section6.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section6.sudo().write({'discount_line': line_discount_line})
						for section7 in order.equipment_line_ids:
							if section7.project_scope.id == section.project_scope.id and section7.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section7.sudo().write({'discount_line': line_discount_line})
						for section8 in order.subcon_line_ids:
							if section8.project_scope.id == section.project_scope.id and section8.section_name.id == section.section.id:
								line_discount_line = (section1.subtotal + section1.adjustment_line) * (section.discount_amount_section/100)
								section8.sudo().write({'discount_line': line_discount_line})
						for section2 in order.project_scope_ids:
							prd_section = order.section_ids.filtered(lambda p: p.project_scope.id == section2.project_scope.id)
							if section2.project_scope.id == section.project_scope.id:
								line_discount_line = sum(prd_section.mapped('section_discount'))
								section2.sudo().write({'scope_discount': line_discount_line})
						for section3 in order.variable_ids:
							if section3.project_scope.id == section.project_scope.id and section3.section.id == section.section.id:
								line_discount_line = (section3.subtotal_variable + section3.variable_adjustment) * (section.discount_amount_section/100)
								section3.sudo().write({'variable_discount': line_discount_line})
						for section9 in order.manufacture_line:
							if section9.project_scope.id == section.project_scope.id and section9.section.id == section.section.id:
								line_discount_line = (section9.subtotal_manuf + section9.manuf_adjustment) * (section.discount_amount_section/100)
								section9.sudo().write({'manuf_discount': line_discount_line})
			
			# elif order.discount_type == 'variable':
			# 	# order.discount_scope = 0
			# 	# order.discount_section = 0
			# 	# order.discount_manuf = 0
			# 	# order.discount_sub = 0
			# 	# order.line_discount = 0
			# 	for variable in order.variable_ids:
			# 		if variable.discount_method_variable == 'fix':
			# 			variable.variable_discount = variable.discount_amount_variable
			# 			order.discount_sub = sum(order.variable_ids.mapped('variable_discount'))
			# 			prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section_name.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 			number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)
			#
			# 			for variable1 in order.material_line_ids:
			# 				if variable1.project_scope.id == variable.project_scope.id and variable1.section_name.id == variable.section.id and variable1.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable1.sudo().write({'discount_line': line_discount_line})
			# 			for variable4 in order.labour_line_ids:
			# 				if variable4.project_scope.id == variable.project_scope.id and variable4.section_name.id == variable.section.id and variable4.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable4.sudo().write({'discount_line': line_discount_line})
			# 			for variable5 in order.overhead_line_ids:
			# 				if variable5.project_scope.id == variable.project_scope.id and variable5.section_name.id == variable.section.id and variable5.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable5.sudo().write({'discount_line': line_discount_line})
			# 			for variable6 in order.internal_asset_line_ids:
			# 				if variable6.project_scope.id == variable.project_scope.id and variable6.section_name.id == variable.section.id and variable6.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable6.sudo().write({'discount_line': line_discount_line})
			# 			for variable7 in order.equipment_line_ids:
			# 				if variable7.project_scope.id == variable.project_scope.id and variable7.section_name.id == variable.section.id and variable7.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable7.sudo().write({'discount_line': line_discount_line})
			# 			for variable8 in order.subcon_line_ids:
			# 				if variable8.project_scope.id == variable.project_scope.id and variable8.section_name.id == variable.section.id and variable8.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_all_lines)
			# 					variable8.sudo().write({'discount_line': line_discount_line})
			# 			for variable2 in order.project_scope_ids:
			# 				prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == variable2.project_scope.id)
			# 				if variable2.project_scope.id == variable.project_scope.id:
			# 					line_discount_line = sum(prd_scope.mapped('variable_discount'))
			# 					variable2.sudo().write({'scope_discount': line_discount_line})
			# 			for variable3 in order.section_ids:
			# 				prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == variable3.project_scope.id and p.section.id == variable3.section.id)
			# 				if variable3.project_scope.id == variable.project_scope.id and variable3.section.id == variable.section.id:
			# 					line_discount_line = sum(prd_section.mapped('variable_discount'))
			# 					variable3.sudo().write({'section_discount': line_discount_line})
			# 			for variable9 in order.manufacture_line:
			# 				prd_manuf = order.manufacture_line.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 				number_of_lines = len(prd_manuf)
			# 				if variable9.project_scope.id == variable.project_scope.id and variable9.section.id == variable.section.id and variable9.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_lines)
			# 					variable9.sudo().write({'manuf_discount': line_discount_line})
			#
			# 		else:
			# 			variable.variable_discount = (variable.subtotal_variable + variable.variable_adjustment) * (variable.discount_amount_variable / 100)
			# 			order.discount_sub = sum(order.variable_ids.mapped('variable_discount'))
			# 			for variable1 in order.material_line_ids:
			# 				if variable1.project_scope.id == variable.project_scope.id and variable1.section_name.id == variable.section.id and variable1.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable1.subtotal + variable1.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable1.sudo().write({'discount_line': line_discount_line})
			# 			for variable4 in order.labour_line_ids:
			# 				if variable4.project_scope.id == variable.project_scope.id and variable4.section_name.id == variable.section.id and variable4.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable4.subtotal + variable4.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable4.sudo().write({'discount_line': line_discount_line})
			# 			for variable5 in order.overhead_line_ids:
			# 				if variable5.project_scope.id == variable.project_scope.id and variable5.section_name.id == variable.section.id and variable5.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable5.subtotal + variable5.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable5.sudo().write({'discount_line': line_discount_line})
			# 			for variable6 in order.internal_asset_line_ids:
			# 				if variable6.project_scope.id == variable.project_scope.id and variable6.section_name.id == variable.section.id and variable6.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable6.subtotal + variable6.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable6.sudo().write({'discount_line': line_discount_line})
			# 			for variable7 in order.equipment_line_ids:
			# 				if variable7.project_scope.id == variable.project_scope.id and variable7.section_name.id == variable.section.id and variable7.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable7.subtotal + variable7.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable7.sudo().write({'discount_line': line_discount_line})
			# 			for variable8 in order.subcon_line_ids:
			# 				if variable8.project_scope.id == variable.project_scope.id and variable8.section_name.id == variable.section.id and variable8.variable_ref.id == variable.variable.id:
			# 					line_discount_line = (variable8.subtotal + variable8.adjustment_line) * (variable.discount_amount_variable/100)
			# 					variable8.sudo().write({'discount_line': line_discount_line})
			# 			for variable2 in order.project_scope_ids:
			# 				prd_scope = order.variable_ids.filtered(lambda p: p.project_scope.id == variable2.project_scope.id)
			# 				if variable2.project_scope.id == variable.project_scope.id:
			# 					line_discount_line = sum(prd_scope.mapped('variable_discount'))
			# 					variable2.sudo().write({'scope_discount': line_discount_line})
			# 			for variable3 in order.section_ids:
			# 				prd_section = order.variable_ids.filtered(lambda p: p.project_scope.id == variable3.project_scope.id and p.section.id == variable3.section.id)
			# 				if variable3.project_scope.id == variable.project_scope.id and variable3.section.id == variable.section.id:
			# 					line_discount_line = sum(prd_section.mapped('variable_discount'))
			# 					variable3.sudo().write({'section_discount': line_discount_line})
			# 			for variable9 in order.manufacture_line:
			# 				prd_manuf = order.manufacture_line.filtered(lambda p: p.project_scope.id == variable.project_scope.id and p.section.id == variable.section.id and p.variable_ref.id == variable.variable.id)
			# 				number_of_lines = len(prd_manuf)
			# 				if variable9.project_scope.id == variable.project_scope.id and variable9.section.id == variable.section.id and variable9.variable_ref.id == variable.variable.id:
			# 					line_discount_line = variable.variable_discount / float(number_of_lines)
			# 					variable9.sudo().write({'manuf_discount': line_discount_line})

			
			elif order.discount_type == 'manuf':
				# order.discount_scope = 0
				# order.discount_section = 0
				# order.discount_variable = 0
				# order.discount_sub = 0
				# order.line_discount = 0
				for manuf in order.manufacture_line:
					if manuf.discount_method_manuf == 'fix':
						manuf.manuf_discount = manuf.discount_amount_manuf
						order.discount_sub = sum(order.manufacture_line.mapped('manuf_discount'))
						prd_line1 = order.material_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line2 = order.labour_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line3 = order.overhead_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line4 = order.internal_asset_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line5 = order.equipment_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						prd_line6 = order.subcon_line_ids.filtered(lambda p: p.project_scope.id == manuf.project_scope.id and p.section_name.id == manuf.section.id and p.variable_ref.id == manuf.variable_ref.id and p.finish_good_id.id == manuf.finish_good_id.id and p.bom_id.id == manuf.bom_id.id)
						number_of_all_lines = len(prd_line1) + len(prd_line2) + len(prd_line3) + len(prd_line4) + len(prd_line5) + len(prd_line6)

						for manuf1 in order.material_line_ids:
							if manuf1.project_scope.id == manuf.project_scope.id and manuf1.section_name.id == manuf.section.id and manuf1.variable_ref.id == manuf.variable_ref.id and manuf1.finish_good_id.id == manuf.finish_good_id.id and manuf1.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf1.sudo().write({'discount_line': line_discount_line})
						for manuf2 in order.labour_line_ids:
							if manuf2.project_scope.id == manuf.project_scope.id and manuf2.section_name.id == manuf.section.id and manuf2.variable_ref.id == manuf.variable_ref.id and manuf2.finish_good_id.id == manuf.finish_good_id.id and manuf2.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf2.sudo().write({'discount_line': line_discount_line})
						for manuf3 in order.overhead_line_ids:
							if manuf3.project_scope.id == manuf.project_scope.id and manuf3.section_name.id == manuf.section.id and manuf3.variable_ref.id == manuf.variable_ref.id and manuf3.finish_good_id.id == manuf.finish_good_id.id and manuf3.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf3.sudo().write({'discount_line': line_discount_line})
						for manuf4 in order.internal_asset_line_ids:
							if manuf4.project_scope.id == manuf.project_scope.id and manuf4.section_name.id == manuf.section.id and manuf4.variable_ref.id == manuf.variable_ref.id and manuf4.finish_good_id.id == manuf.finish_good_id.id and manuf4.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf4.sudo().write({'discount_line': line_discount_line})
						for manuf5 in order.equipment_line_ids:
							if manuf5.project_scope.id == manuf.project_scope.id and manuf5.section_name.id == manuf.section.id and manuf5.variable_ref.id == manuf.variable_ref.id and manuf5.finish_good_id.id == manuf.finish_good_id.id and manuf5.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf5.sudo().write({'discount_line': line_discount_line})
						for manuf6 in order.subcon_line_ids:
							if manuf6.project_scope.id == manuf.project_scope.id and manuf6.section_name.id == manuf.section.id and manuf6.variable_ref.id == manuf.variable_ref.id and manuf6.finish_good_id.id == manuf.finish_good_id.id and manuf6.bom_id.id == manuf.bom_id.id:
								line_discount_line = manuf.manuf_discount / float(number_of_all_lines)
								manuf6.sudo().write({'discount_line': line_discount_line})
						for manuf7 in order.project_scope_ids:
							prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf7.project_scope.id)
							if manuf7.project_scope.id == manuf.project_scope.id:
								line_discount_line = sum(prd_scope.mapped('manuf_discount'))
								manuf7.sudo().write({'scope_discount': line_discount_line})
						for manuf8 in order.section_ids:
							prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf8.project_scope.id and p.section.id == manuf8.section.id)
							if manuf8.project_scope.id == manuf.project_scope.id and manuf8.section.id == manuf.section.id:
								line_discount_line = sum(prd_section.mapped('manuf_discount'))
								manuf8.sudo().write({'section_discount': line_discount_line})
						for manuf9 in order.variable_ids:
							prd_variable = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf9.project_scope.id and p.section.id == manuf9.section.id and p.variable_ref.id == manuf9.variable.id)
							if manuf9.project_scope.id == manuf.project_scope.id and manuf9.section.id == manuf.section.id and manuf9.variable.id == manuf.variable_ref.id:
								line_discount_line = sum(prd_variable.mapped('manuf_discount'))
								manuf9.sudo().write({'variable_discount': line_discount_line})

					else:
						manuf.manuf_discount = (manuf.subtotal_manuf + manuf.manuf_adjustment) * (manuf.discount_amount_manuf / 100)
						order.discount_sub = sum(order.manufacture_line.mapped('manuf_discount'))
						for manuf1 in order.material_line_ids:
							if manuf1.project_scope.id == manuf.project_scope.id and manuf1.section_name.id == manuf.section.id and manuf1.variable_ref.id == manuf.variable_ref.id and manuf1.finish_good_id.id == manuf.finish_good_id.id and manuf1.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf1.subtotal + manuf1.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf1.sudo().write({'discount_line': line_discount_line})
						for manuf2 in order.labour_line_ids:
							if manuf2.project_scope.id == manuf.project_scope.id and manuf2.section_name.id == manuf.section.id and manuf2.variable_ref.id == manuf.variable_ref.id and manuf2.finish_good_id.id == manuf.finish_good_id.id and manuf2.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf2.subtotal + manuf2.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf2.sudo().write({'discount_line': line_discount_line})
						for manuf3 in order.overhead_line_ids:
							if manuf3.project_scope.id == manuf.project_scope.id and manuf3.section_name.id == manuf.section.id and manuf3.variable_ref.id == manuf.variable_ref.id and manuf3.finish_good_id.id == manuf.finish_good_id.id and manuf3.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf3.subtotal + manuf3.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf3.sudo().write({'discount_line': line_discount_line})
						for manuf4 in order.internal_asset_line_ids:
							if manuf4.project_scope.id == manuf.project_scope.id and manuf4.section_name.id == manuf.section.id and manuf4.variable_ref.id == manuf.variable_ref.id and manuf4.finish_good_id.id == manuf.finish_good_id.id and manuf4.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf4.subtotal + manuf4.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf4.sudo().write({'discount_line': line_discount_line})
						for manuf5 in order.equipment_line_ids:
							if manuf5.project_scope.id == manuf.project_scope.id and manuf5.section_name.id == manuf.section.id and manuf5.variable_ref.id == manuf.variable_ref.id and manuf5.finish_good_id.id == manuf.finish_good_id.id and manuf5.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf5.subtotal + manuf5.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf5.sudo().write({'discount_line': line_discount_line})
						for manuf6 in order.subcon_line_ids:
							if manuf6.project_scope.id == manuf.project_scope.id and manuf6.section_name.id == manuf.section.id and manuf6.variable_ref.id == manuf.variable_ref.id and manuf6.finish_good_id.id == manuf.finish_good_id.id and manuf6.bom_id.id == manuf.bom_id.id:
								line_discount_line = (manuf6.subtotal + manuf6.adjustment_line) * (manuf.discount_amount_manuf/100)
								manuf6.sudo().write({'discount_line': line_discount_line})
						for manuf7 in order.project_scope_ids:
							prd_scope = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf7.project_scope.id)
							if manuf7.project_scope.id == manuf.project_scope.id:
								line_discount_line = sum(prd_scope.mapped('manuf_discount'))
								manuf7.sudo().write({'scope_discount': line_discount_line})
						for manuf8 in order.section_ids:
							prd_section = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf8.project_scope.id and p.section.id == manuf8.section.id)
							if manuf8.project_scope.id == manuf.project_scope.id and manuf8.section.id == manuf.section.id:
								line_discount_line = sum(prd_section.mapped('manuf_discount'))
								manuf8.sudo().write({'section_discount': line_discount_line})
						for manuf9 in order.variable_ids:
							prd_variable = order.manufacture_line.filtered(lambda p: p.project_scope.id == manuf9.project_scope.id and p.section.id == manuf9.section.id and p.variable_ref.id == manuf9.variable.id)
							if manuf9.project_scope.id == manuf.project_scope.id and manuf9.section.id == manuf.section.id and manuf9.variable.id == manuf.variable_ref.id:
								line_discount_line = sum(prd_variable.mapped('manuf_discount'))
								manuf9.sudo().write({'variable_discount': line_discount_line})

			else:
				# order.discount_scope = 0
				# order.discount_section = 0
				# order.discount_variable = 0
				# order.discount_manuf = 0
				order.discount_sub = 0
				# order.line_discount = 0

			
			for line1 in order.project_scope_ids:
				line_amount_line1 = (line1.subtotal_scope + line1.scope_adjustment) - line1.scope_discount
				line1.sudo().write({'amount_line': line_amount_line1})
			
			for line2 in order.section_ids:
				line_amount_line2 = (line2.subtotal_section + line2.section_adjustment) - line2.section_discount
				line2.sudo().write({'amount_line': line_amount_line2})

			for line3 in order.variable_ids:
				line_amount_line3 = (line3.subtotal_variable + line3.variable_adjustment) - line3.variable_discount
				line3.sudo().write({'amount_line': line_amount_line3})
			
			for line10 in order.manufacture_line:
				line_amount_line10 = (line10.subtotal_manuf + line10.manuf_adjustment) - line10.manuf_discount
				line10.sudo().write({'amount_line': line_amount_line10})
			
			for line4 in order.material_line_ids:
				line_amount_line4 = (line4.subtotal + line4.adjustment_line) - line4.discount_line
				line4.sudo().write({'amount_line': line_amount_line4})
				line_total_amount4 = line4.amount_line + line4.amount_tax_line
				line4.sudo().write({'total_amount': line_total_amount4})
			
			for line5 in order.labour_line_ids:
				line_amount_line5 = (line5.subtotal + line5.adjustment_line) - line5.discount_line
				line5.sudo().write({'amount_line': line_amount_line5})
				line_total_amount5 = line5.amount_line + line5.amount_tax_line
				line5.sudo().write({'total_amount': line_total_amount5})

			for line6 in order.overhead_line_ids:
				line_amount_line6 = (line6.subtotal + line6.adjustment_line) - line6.discount_line
				line6.sudo().write({'amount_line': line_amount_line6})
				line_total_amount6 = line6.amount_line + line6.amount_tax_line
				line6.sudo().write({'total_amount': line_total_amount6})
			
			for line7 in order.subcon_line_ids:
				line_amount_line7 = (line7.subtotal + line7.adjustment_line) - line7.discount_line
				line7.sudo().write({'amount_line': line_amount_line7})
				line_total_amount7 = line7.amount_line + line7.amount_tax_line
				line7.sudo().write({'total_amount': line_total_amount7})
			
			for line8 in order.equipment_line_ids:
				line_amount_line8 = (line8.subtotal + line8.adjustment_line) - line8.discount_line
				line8.sudo().write({'amount_line': line_amount_line8})
				line_total_amount8 = line8.amount_line + line8.amount_tax_line
				line8.sudo().write({'total_amount': line_total_amount8})
			
			for line9 in order.internal_asset_line_ids:
				line_amount_line9 = (line9.subtotal + line9.adjustment_line) - line9.discount_line
				line9.sudo().write({'amount_line': line_amount_line9})
				line_total_amount9 = line9.amount_line + line9.amount_tax_line
				line9.sudo().write({'total_amount': line_total_amount9})
			
								
			# order.contract_amount = order.amount_untaxed + order.adjustment_scope + order.adjustment_section + order.adjustment_variable + order.adjustment_manuf + order.adjustment_sub + order.line_adjustment - order.discount_scope - order.discount_section - order.discount_variable - order.discount_manuf - order.discount_sub - order.line_discount 
			
			order.contract_amount = order.amount_untaxed + order.adjustment_sub - order.discount_sub 
			order.amount_total = order.contract_amount + order.amount_tax

			return order.amount_total


class ToManufactureLine(models.Model):
	_name = 'sale.manufacture.line'
	_description = 'Sale Manufacre Line'
	_order = 'sequence'

	sale_cons_id = fields.Many2one('sale.order.const', string='Order Reference', required=True, ondelete='cascade', index=True, copy=False) 
	active = fields.Boolean(related='sale_cons_id.active', string='Active')
	sequence = fields.Integer(string="sequence", default=0)
	sr_no = fields.Integer('No.', compute="_sequence_ref")
	project_scope = fields.Many2one('project.scope.line', 'Project Scope', required=True)
	section = fields.Many2one('section.line','Section', required=True)
	variable_ref = fields.Many2one('variable.template', string='Variable')
	finish_good_id = fields.Many2one('product.product', 'Finished Goods', required=True)
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
	cascaded = fields.Boolean(string="Cascaded", default=False)
	is_child = fields.Boolean(string="Is child", default=False)
	parent_manuf_line = fields.Many2one('mrp.bom', string='Parent BOM')
	bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
	quantity = fields.Float('Quantity')
	uom_id = fields.Many2one('uom.uom','Unit Of Measure')
	adjustment_method_manuf = fields.Selection([
						('fix', 'Fixed'),
						('per', 'Percentage')
						],string="Adjustment Method")
	adjustment_amount_manuf = fields.Float(string="Adjustment Amount")
	adjustment_subtotal_manuf = fields.Float(string="Adjustment Subtotal")
	manuf_adjustment = fields.Float(string="Adjustment Line")
	discount_method_manuf = fields.Selection([
						('fix', 'Fixed'),
						('per', 'Percentage')
						],string="Discount Method")
	discount_amount_manuf = fields.Float(string="Discount Amount")
	discount_subtotal_manuf = fields.Float(string="Discount Subtotal")
	manuf_discount = fields.Float(string="Discount Line")
	discount_type = fields.Selection(related='sale_cons_id.discount_type', string="Discount Applies to")
	adjustment_type = fields.Selection(related='sale_cons_id.adjustment_type', string="Adjustment Applies to")
	subtotal_manuf = fields.Float(string="Subtotal")
	amount_line = fields.Float(string="Amount Line")
	currency_id = fields.Many2one(related='sale_cons_id.currency_id', depends=['sale_cons_id.currency_id'], string='Currency', store=True, readonly=True)
	company_id = fields.Many2one(related='sale_cons_id.company_id', string='Company', readonly=True, store=True, index=True)
	state_line = fields.Selection(related='sale_cons_id.state', string='Order Status')
	project_id = fields.Many2one(related='sale_cons_id.project_id', string="Project")
	job_reference = fields.Many2one(related='sale_cons_id.job_reference', string="BOQ Reference")
	job_references = fields.Many2many(related='sale_cons_id.job_references', string="BOQ Reference")
	customer_id = fields.Many2one(related='sale_cons_id.partner_id', string='Customer')
	user_id = fields.Many2many(related='sale_cons_id.user_id', string='Salesperson')
	sequence_no = fields.Char(related='sale_cons_id.name', string="Sequence Number")
	analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

	@api.depends('sale_cons_id.manufacture_line')
	def _sequence_ref(self):
		for line in self:
			no = 0
			line.sr_no = no
			for l in line.sale_cons_id.manufacture_line:
				no += 1
				l.sr_no = no


class SaleOrderMaterialLine(models.Model):
	_inherit = 'sale.order.material.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SaleOrderlabourLine(models.Model):
	_inherit = 'sale.order.labour.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SaleOrderoverheadLine(models.Model):
	_inherit = 'sale.order.overhead.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SaleOrderInternalAsset(models.Model):
	_inherit = 'sale.internal.asset.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SaleOrderEquipmentLine(models.Model):
	_inherit = 'sale.order.equipment.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SaleOrdersubconLine(models.Model):
	_inherit = 'sale.order.subcon.line'

	finish_good_id = fields.Many2one('product.product', 'Finished Goods')
	bom_id = fields.Many2one('mrp.bom', 'BOM')
	final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
