from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MRPNotification(models.Model):
	_name = 'mrp.notification'
	_description = 'MRP Notification'

	def _default_is_required_mrp_branch(self):
		notif_type = self.env.context.get('default_type')
		if notif_type == 'email':
			return self.env.company.send_email_so_confirm
		return self.env.company.send_system_so_confirm

	@api.model
	def create(self, vals):
		branch_id = vals.get('branch_id')
		mrp_notification_id = self.search([('branch_id', '=', branch_id), ('type', '=', vals.get('type'))])
		if mrp_notification_id:
			raise ValidationError(_(
				f"The branch already created for {vals.get('type')} notification setting. Please choose another branch"
			))
		branch_id = self.env['res.branch'].browse(branch_id)
		notif_type = vals.get('type') == 'email' and 'E-Mail' or 'System'
		vals['name'] = f'{branch_id.name} {notif_type} Notification'
		return super(MRPNotification, self).create(vals)

	def write(self, vals):
		if vals.get('branch_id'):
			branch_id = vals.get('branch_id')
			mrp_notification_id = self.search([('branch_id', '=', branch_id), ('type', '=', self.type)])
			if mrp_notification_id:
				raise ValidationError(_(
					f"The branch already created for {self.type} notification setting. Please choose another branch"
				))
		return super(MRPNotification, self).write(vals)

	name = fields.Char(string='Name', readonly=True, copy=False, default=lambda self: _('New'))
	type = fields.Selection([('email', 'Email'), ('system', 'System'), ('whatsapp', 'WhatsApp')], required=True)
	branch_id = fields.Many2one('res.branch', string='Branch', required=True)
	mrp_branch_id = fields.Many2one('res.branch', string='Production Branch')
	receiver_ids = fields.One2many('mrp.notification.receiver', 'notification_id', string='Receiver')
	is_required_mrp_branch = fields.Boolean(default=_default_is_required_mrp_branch)


class MRPNotificationReceiver(models.Model):
	_name = 'mrp.notification.receiver'
	_description = 'MRP Notification Receiver'

	notification_id = fields.Many2one('mrp.notification', readonly=True, copy=False)
	user_id = fields.Many2one('res.users', string='Receiver', required=True)
