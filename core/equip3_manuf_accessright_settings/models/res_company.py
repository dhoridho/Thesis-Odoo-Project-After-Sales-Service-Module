from odoo import models, fields


class ResCompany(models.Model):
	_name = 'res.company'
	_inherit = 'res.company'

	manufacturing_plan_conf = fields.Boolean('Production Plan Approval Matrix', default=True)
	manufacturing_order_conf = fields.Boolean('Production Order Approval Matrix', default=True)
	mrp_plan_partial_availability = fields.Boolean('MP Reserve Materials Partially', default=False)
	production_record_conf = fields.Boolean('Production Record Approval Matrix', default=True, store=True)
	mrp_production_partial_availability = fields.Boolean('Production Orders Reserve Materials Partially', default=False)
	mrp_force_done = fields.Boolean(string='Production Order Allow Force Done', readonly=False)
	mo_force_done = fields.Boolean(string='Production Plan Allow Force Done', readonly=False)
	mo_auto_reserve_availability_materials = fields.Boolean(string='Production Order Auto Reserve Materials', readonly=False)
	mp_auto_reserve_availability_materials = fields.Boolean(string='Production Plan Auto Reserve Materials', readonly=False)
	send_wa_approval_notification_mrp = fields.Boolean('Production Order WhatsApp Notification', default=True)
	send_wa_approval_notification_mp = fields.Boolean('Production Plan WhatsApp Notification', default=True)
	send_wa_approval_notification_mpr = fields.Boolean('Production Record WhatsApp Notification', default=True)

	manufacturing_mps = fields.Boolean(string='Master Production Schedule')
	manufacturing_period = fields.Selection([
		('month', 'Monthly'),
		('week', 'Weekly'),
		('day', 'Daily')], string="Manufacturing Period",
		default='month', required=True,
		help="Default value for the time ranges in Master Production Schedule report.")

	manufacturing_period_to_display = fields.Integer('Number of columns for the given period to display in Master Production Schedule', default=12)

	# unused fields, may delete someday
	mrp_submit_purchase_request = fields.Boolean(string='Allow Submit Purchase Request', readonly=False)
	mrp_submit_material_request = fields.Boolean(string='Allow Submit Materials Request', readonly=False)

	def write(self, vals):
		res = super(ResCompany, self).write(vals)
		manufacturing_menu = self.env.ref("mrp.menu_mrp_root")
		for company in self:
			if not company == self.env.company:
				continue
			manufacturing_menu.active = company.manufacturing
		return res
