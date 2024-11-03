from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta

class ForceDoneMemory(models.TransientModel):
	_name = 'force.done.memory'
	_description = "Force Done Memory"
	
	blanket_id = fields.Many2one('saleblanket.saleblanket', 'Source', required=True)
	qty = fields.Float("All Qty")
	remaining_qty = fields.Float("Remaining Qty")
	reason = fields.Text("Reason")
	
	def action_wiz_2(self):
		return {
			'type': 'ir.actions.act_window',
			'name': _('Forced Done Wizard'),
			'res_model': 'force.done.memory',
			'view_type': 'form',
			'view_mode': 'form',
			'view_id': self.env.ref('equip3_sale_other_operation_cont.force_done_memory_form2').id,
			'target': 'new',
			'context': {
				'default_blanket_id': self.blanket_id.id,
				'default_qty': self.qty,
				'default_remaining_qty': self.remaining_qty,
			},
		}
	
	def action_wiz_3(self):
		for res in self:
			if res.reason:
				res.blanket_id.action_force_done(res.reason)
			else:
				raise ValidationError("Reason cannot be empty to perform this action.")
	
	def action_wiz_4(self):
		return {
			'type': 'ir.actions.act_window',
			'name': _('Forced Done Wizard'),
			'res_model': 'force.done.memory',
			'view_type': 'form',
			'view_mode': 'form',
			'view_id': self.env.ref('equip3_sale_other_operation_cont.force_done_memory_form1').id,
			'target': 'new',
			'context': {
				'default_blanket_id': self.id,
				'default_qty': self.qty,
				'default_remaining_qty': self.remaining_qty,
			},
		}