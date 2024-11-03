# # -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import xlwt
import xlsxwriter
import base64
from io import BytesIO


class MrpInherited(models.Model):
	_inherit = 'mrp.production'

	total_material = fields.Float(string='Material Cost', digits='Product Unit of Measure')
	total_byproduct = fields.Float(string='By-Product Cost', digits='Product Unit of Measure')
	total_overhead = fields.Float(string='Overhead Cost', digits='Product Unit of Measure')
	total_labor = fields.Float(string='Labor Cost', digits='Product Unit of Measure')
	total_subcontracting = fields.Float(string='Subcontracting Cost', digits='Product Unit of Measure')
	qty_produced = fields.Float(compute="_get_produced_qty", string="Quantity Produced", store=True)
	svl_cost = fields.Float(string='SVL Cost', digits='Product Unit of Measure')
	svl_unit_cost = fields.Float(string='SVL Unit Cost', digits='Product Unit of Measure')

	def compute_svl_cost(self):
		for record in self:
			svl_ids = record.stock_valuation_layer_ids
			mca_ids = record.mca_production_ids.filtered(lambda m: m.mrp_cost_actualization_id.state == 'post')

			total_byproduct = abs(sum(svl_ids.filtered(lambda s: s.type == 'byproduct').mapped('value')))
			total_material = abs(sum(svl_ids.filtered(lambda s: s.type == 'component').mapped('value'))) + sum(mca_ids.mapped('total_material'))
			total_overhead = abs(sum(svl_ids.filtered(lambda s: s.type == 'mca_overhead').mapped('value'))) + sum(mca_ids.mapped('total_overhead'))
			total_labor = abs(sum(svl_ids.filtered(lambda s: s.type == 'mca_labor').mapped('value'))) + sum(mca_ids.mapped('total_labor'))
			total_subcontracting = abs(sum(svl_ids.filtered(lambda s: s.type == 'subcon').mapped('value'))) + sum(mca_ids.mapped('total_subcontracting'))

			svl_cost = total_material + total_overhead + total_labor - total_byproduct + total_subcontracting

			if record.product_qty:
				svl_unit_cost = svl_cost / record.product_qty
			else:
				svl_unit_cost = 0.0

			record.write({
				'total_byproduct': total_byproduct,
				'total_material': total_material,
				'total_overhead': total_overhead,
				'total_labor': total_labor,
				'total_subcontracting': total_subcontracting,
				'svl_cost': svl_cost,
				'svl_unit_cost': svl_unit_cost
			})

	def recompute_and_go(self):
		self.sudo().search([]).compute_svl_cost()
		action = self.env['ir.actions.actions']._for_xml_id('equip3_manuf_reports.action_mrp_production_cost_analysis_computes')
		return action

	def print_pdf_preview1(self):
		return {
			'name': 'Production Cost Analysis',
			'type': 'ir.actions.report',
			'report_name': 'equip3_manuf_reports.temp_mrp_cost_analysis',
			'model': 'mrp.cost.analysis',
			'report_type': 'qweb-html'
		}

	def print_xlsx_preview(self):
		return {
			'name': 'XLSX',
			'type': 'ir.actions.report',
			'report_name': 'report_xlsx.partner_xlsx',
			'model': 'res.partner',
			'report_type': 'xlsx'
		}
	def print_xlsx(self):
		workbook = xlwt.Workbook(encoding="UTF-8")
		format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
		formathead2 = xlwt.easyxf('font:height 250,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
		format1 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
		format2 = xlwt.easyxf('font:bold True;align: horiz left')
		format3 = xlwt.easyxf('align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
		sheet = workbook.add_sheet("Payslip Summary Report")
		sheet.col(0).width = int(7 * 260)
		sheet.col(1).width = int(30 * 260)
		sheet.col(2).width = int(40 * 260)
		sheet.col(3).width = int(20 * 260)
		sheet.row(0).height_mismatch = True
		sheet.row(0).height = 150 * 4
		sheet.row(1).height_mismatch = True
		sheet.row(1).height = 150 * 2
		sheet.row(2).height_mismatch = True
		sheet.row(2).height = 150 * 3
		sheet.write_merge(0, 0, 0, 3, 'Production Cost Analysis Report', format0)
		sheet.write(1, 0, 'Production Order', format1)
		sheet.write(1, 1, 'Production Date', format1)
		sheet.write(1, 2, 'Product', format1)
		sheet.write(1, 3, 'Unit Of Measure', format1)
		sheet.write(1, 4, 'Quantity', format1)
		sheet.write(1, 5, 'Materials', format1)
		sheet.write(1, 6, 'Overhead', format1)
		sheet.write(1, 7, 'Labor', format1)
		sheet.write(1, 8, 'By Product', format1)
		sheet.write(1, 9, 'Total Cost', format1)
		sheet.write(1, 10, 'Unit Cost', format1)
		active_ids = self._context.get('active_ids', []) or []
		records = self.env['mrp.production'].browse(active_ids)
		row = 2
		for rec in records:
			sheet.write(row, 0, rec.name, format1)
			sheet.write(row, 1, rec.date_planned_start, format1)
			sheet.write(row, 2, rec.product_id.name, format1)
			sheet.write(row, 3, rec.product_uom_id.name, format1)
			sheet.write(row, 4, rec.product_qty, format1)
			sheet.write(row, 5, rec.total_material, format1)
			sheet.write(row, 6, rec.total_overhead, format1)
			sheet.write(row, 7, rec.total_labor, format1)
			sheet.write(row, 8, rec.total_byproduct, format1)
			sheet.write(row, 9, rec.svl_cost, format1)
			sheet.write(row, 10, rec.svl_unit_cost, format1)
			row+=1
		stream = BytesIO()
		workbook.save(stream)
		file_xlsx = self.env['mrp.cost.analysis.xlsx'].create(
			{'file_xlsx': base64.encodestring(stream.getvalue())})
		stream.close()
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'mrp.cost.analysis.xlsx',
			'view_mode': 'form',
			'view_type': 'form',
			'res_id': file_xlsx.id,
			'target': 'new',
		}


class MRPCostAnalysisXLSX(models.Model):
	_name = 'mrp.cost.analysis.xlsx'
	_description = 'MRP Cost Analysis XLSX'

	file_xlsx = fields.Binary('Excel Report', readonly=True, store=True)
