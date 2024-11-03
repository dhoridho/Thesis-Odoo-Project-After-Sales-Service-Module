
from odoo import fields, models

class PosSalesSummaryWizard(models.TransientModel):
	_inherit = "pos.sale.summary.wizard"


	is_ph_template = fields.Boolean('Philippines Template',default=True)


class SaleSummaryReportWizard(models.AbstractModel):
	_inherit = "report.equip3_pos_report.report_sales_summary"

	def _get_report_values(self, docids, data=None):
		res = super(SaleSummaryReportWizard, self)._get_report_values(docids,data)
		res['o'] = self.env['pos.sale.summary.wizard'].browse(docids)
		res['is_ph_template'] = self.env['pos.sale.summary.wizard'].browse(docids).is_ph_template	
		return res


	def count_ph_vat_breakdown(self,line,ph_vat_breakdown):
		if not ph_vat_breakdown:
			ph_vat_breakdown = {'VATable':0,'VAT zero rate':0,'VAT exempt':0}

		if line.product_id.ph_vat_type == 'VATable':
			ph_vat_breakdown['VATable'] += line.untax_amount
		if line.product_id.ph_vat_type == 'VAT zero rate':
			ph_vat_breakdown['VAT zero rate'] += line.untax_amount
		if line.product_id.ph_vat_type == 'VAT exempt':
			ph_vat_breakdown['VAT exempt'] += line.untax_amount
		return ph_vat_breakdown