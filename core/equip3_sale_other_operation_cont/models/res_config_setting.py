from odoo import models, fields
from odoo.exceptions import UserError, ValidationError, Warning

class ResConfigSetting(models.TransientModel):
	_inherit = 'res.config.settings'
	
	bo_expiry_date = fields.Integer(
		string="Default Expiry Date",
		default=30
	)
	bo_before_exp_notify = fields.Boolean(
		string="Notify Before Expiry Date")
	bo_days_before_exp_notify = fields.Integer(
		string="Notify Before Expiry Date")
	bo_on_date_notify = fields.Boolean(
		string="On Date Notification")
	bo_approval_email_notify = fields.Boolean(
		string="Email Notification Approval")
	bo_approval_wa_notify = fields.Boolean(
		string="Whatsapp Notification Approval")
	# is_quantity = fields.Boolean(string="Quantity")
	# is_quantity_sequence = fields.Selection([
	# 	('first', 'First'),
	# 	('last', 'Last'),
	# ], string='Approval Sequence', default='first', help="Define the sequence number in blanket order approval matrix process for each configuration")
	# is_total_amounts = fields.Boolean(string="Amount")
	# is_total_amount_sequence = fields.Selection([
	# 	('first', 'First'),
	# 	('last', 'Last'),
	# ], string='Approval Sequence', default='last', help="Define the sequence number in blanket order approval matrix process for each configuration")
	
	def set_values(self):
		super(ResConfigSetting, self).set_values()
		
		# seq_num = ['first', 'last']
		# if self.is_quantity and self.is_quantity_sequence not in seq_num:
		# 	raise ValidationError("The sequence number for blanket order approval matrix is not sequential. Please rearrange the sequence number")
		# if self.is_total_amounts and self.is_total_amount_sequence not in seq_num:
		# 	raise ValidationError("The sequence number for blanket order approval matrix is not sequential. Please rearrange the sequence number")
		#
		# if self.is_quantity and self.is_total_amounts and self.is_quantity_sequence == self.is_total_amount_sequence:
		# 	raise ValidationError("The sequence number for blanket order approval matrix is not sequential. Please rearrange the sequence number")
		#
		# if self.is_quantity and self.is_total_amounts and self.is_quantity_sequence != 'first':
		# 	raise ValidationError("The sequence number for blanket order approval matrix is not sequential. Please rearrange the sequence number")
		
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_expiry_date', self.bo_expiry_date)
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_before_exp_notify', self.bo_before_exp_notify)
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_days_before_exp_notify', self.bo_days_before_exp_notify)
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_on_date_notify', self.bo_on_date_notify)
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_approval_email_notify', self.bo_approval_email_notify)
		self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.bo_approval_wa_notify', self.bo_approval_wa_notify)
		# self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.is_quantity', self.is_quantity)
		# self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.is_quantity_sequence', self.is_quantity_sequence)
		# self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.is_total_amounts', self.is_total_amounts)
		# self.env['ir.config_parameter'].sudo().set_param('equip3_sale_other_operation_cont.is_total_amount_sequence', self.is_total_amount_sequence)
		# if self.is_bo_approval_matrix:
		# 	self.env.ref('equip3_sale_other_operation_cont.bo_approval_matrix').active = True
		# else:
		# 	self.env.ref('equip3_sale_other_operation_cont.bo_approval_matrix').active = False
	
	def get_values(self):
		res = super(ResConfigSetting, self).get_values()
		res.update({
			'bo_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_expiry_date') or 30,
			'bo_before_exp_notify':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_before_exp_notify'),
			'bo_days_before_exp_notify':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_days_before_exp_notify'),
			'bo_on_date_notify':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_on_date_notify'),
			'bo_approval_email_notify':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_approval_email_notify'),
			'bo_approval_wa_notify':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.bo_approval_wa_notify'),
			# 'is_quantity':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.is_quantity'),
			# 'is_quantity_sequence':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.is_quantity_sequence'),
			# 'is_total_amounts':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.is_total_amounts'),
			# 'is_total_amount_sequence':  self.env['ir.config_parameter'].get_param('equip3_sale_other_operation_cont.is_total_amount_sequence'),
		})
		return res