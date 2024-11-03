import pytz
import logging
import sys
import requests
import json

from datetime import datetime
from odoo.addons.acrux_chat.tools import TIMEOUT, log_request_error
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	@api.depends('mrp_order_ids')
	def _compute_mrp_orders(self):
		for record in self:
			record.mrp_order_count = len(record.mrp_order_ids)

	@api.depends('mrp_plan_ids')
	def _compute_mrp_plans(self):
		for record in self:
			record.mrp_plan_count = len(record.mrp_plan_ids)

	mrp_plan_ids = fields.One2many('mrp.plan', 'sale_order_id', string='Manufacturing Plan')
	mrp_order_ids = fields.One2many('mrp.production', 'sale_order_id', string='Manufacturing Orders')
	mrp_order_count = fields.Integer(compute='_compute_mrp_orders')
	mrp_plan_count = fields.Integer(compute='_compute_mrp_plans')
	sales_to_manufacturing = fields.Boolean(related='company_id.sales_to_manufacturing')

	def _check_for_manufacturing_plan_orders(self):
		self.ensure_one()
		order_lines = self.order_line.filtered(
			lambda line: line.manuf_auto_create in ('auto_mp', 'auto_mo') and line.bom_id)

		if not order_lines:
			return

		order_name = self.name
		company = self.company_id
		branch = self.branch_id
		user = self.env.user
		commitment_date = datetime.min
		mrp_order_ids = self.env['mrp.production']
		mrp_plan_ids = self.env['mrp.plan']

		is_mp_approval_matrix_on = self.env.company.manufacturing_plan_conf
		is_mo_approval_matrix_on = self.env.company.manufacturing_order_conf

		products = order_lines.mapped('product_id')
		quantities = products.with_context(warehouse=self.warehouse_new_id.id, location=False)._compute_quantities_dict(None, None, None)

		for line in order_lines:
			product = line.product_id
			primary_uom = product.uom_id
			bom = line.bom_id
			product_uom_qty = line.product_uom_qty
			product_uom = line.product_uom
			product_qty = product_uom._compute_quantity(product_uom_qty, primary_uom)

			send_to_production_qty = product_uom_qty
			if company.check_availability:
				qty_available = quantities[product.id]['qty_available']
				send_to_production_qty = primary_uom._compute_quantity(product_qty - qty_available, product_uom)
				if send_to_production_qty <= 0:
					continue

			if line.manuf_auto_create == 'auto_mp':
				plan_matrix = self.env['mrp.approval.matrix']
				if is_mp_approval_matrix_on:
					""" Search MP approval matrix that match SO company & branch """
					plan_matrix = self.env['mrp.approval.matrix'].search([
						('company_id', '=', company.id),
						('branch_id', '=', branch.id),
						('matrix_type', '=', 'mp')
					], limit=1)

					if not plan_matrix:
						raise ValidationError(_('Please create approval matrix for manufacturing plan with company %s and branch %s first!' % (company.display_name, branch.display_name)))

				plan = self.env['mrp.plan'].create({
					'name': order_name,
					'branch_id': branch.id,
					'company_id': company.id,
					'ppic_id': user.id,
					'approval_matrix_id': plan_matrix.id,
					'analytic_tag_ids': self.env['mrp.plan']._default_analytic_tags(company_id=company, branch_id=branch)
				})

				wizard = self.env['mrp.production.wizard'].with_context(
					active_model='mrp.plan',
					active_id=plan.id,
					active_ids=plan.ids,
				).create({
					'plan_id': plan.id,
					'line_ids': [(0, 0, {
						'product_id': product.id,
						'product_uom': product_uom.id,
						'product_qty': send_to_production_qty,
						'no_of_mrp': 1,
						'company': company.id,
						'branch_id': branch.id,
						'bom_id': bom.id
					})]
				})
				wizard.confirm()
	 
				try:
					commitment_date = max(commitment_date, max(plan.mrp_order_ids.mapped('date_planned_finished')))
				except ValueError:
					pass
				mrp_plan_ids += plan

			elif line.manuf_auto_create == 'auto_mo':
				order_matrix = self.env['mrp.approval.matrix']
				if is_mo_approval_matrix_on:
					""" Search MO approval matrix that match SO company & branch """
					order_matrix = self.env['mrp.approval.matrix'].search([
						('company_id', '=', company.id),
						('branch_id', '=', branch.id),
						('matrix_type', '=', 'mo')
					], limit=1)

					if not order_matrix:
						raise ValidationError(_('Please create approval matrix for manufacturing order with company %s and branch %s first!' % (company.display_name, branch.display_name)))

				order_values = {
					'product_id': product.id,
					'product_uom_id': product_uom.id,
					'sale_order_id': self.id,
					'bom_id': bom.id,
					'product_qty': send_to_production_qty,
					'company_id': company.id,
					'branch_id': branch.id,
					'approval_matrix_id': order_matrix.id,
				}

				order = self.env['mrp.production'].create(order_values).sudo()
				order.onchange_product_id()
				order.onchange_branch()
				order._onchange_workorder_ids()
				order._onchange_move_raw()
				order._onchange_move_finished()
				order.onchange_workorder_ids()

				try:
					commitment_date = max(commitment_date, order.date_planned_finished)
				except ValueError:
					pass
				
				mrp_order_ids += order
		
		commitment_date = False if commitment_date == datetime.min else commitment_date

		self.write({
			'commitment_date': commitment_date,
			'mrp_plan_ids': [(6, 0, mrp_plan_ids.ids)],
			'mrp_order_ids': [(6, 0, mrp_order_ids.ids)]
		})

	def get_mrp_button(self):
		table = '<table class="table table-borderless"><tbody>'
		for i in range(max([len(self.mrp_order_ids), len(self.mrp_plan_ids)])):
			table += '<tr>'
			try:
				mrp_order_id = self.mrp_order_ids[i]
				table += f'<td><a style="color:#fff;background-color:#875A7B; padding:8px 16px 8px 16px; border-radius:5px" href="/mail/view?model=mrp.production&amp;res_id={mrp_order_id.id}" data-oe-model="mrp.production" data-oe-id="{mrp_order_id.id}">View MO</a></td>'
			except IndexError:
				table += '<td/>'

			try:
				mrp_plan_id = self.mrp_plan_ids[i]
				table += f'<td><a style="color:#fff;background-color:#875A7B; padding:8px 16px 8px 16px; border-radius:5px" href="/mail/view?model=mrp.plan&amp;res_id={mrp_plan_id.id}" data-oe-model="mrp.plan" data-oe-id="{mrp_plan_id.id}">View MP</a></td>'
			except IndexError:
				table += '<td/>'
			table += '</tr>'
			
		table += '</tbody></table>'
		return table

	def get_local_date(self, date):
		user_tz = self.env.user.tz or pytz.utc
		local = pytz.timezone(user_tz)
		local_date = datetime.strftime(pytz.utc.localize(datetime.strptime(datetime.strftime(date, '%m/%d/%Y %H:%M:%S'),
			'%m/%d/%Y %H:%M:%S')).astimezone(local),"%m/%d/%Y %H:%M:%S"
		)
		return local_date

	def _send_email_notification(self):
		user_ids = self.env['mrp.notification'].search([('type', '=', 'email')]).mapped('receiver_ids').mapped('user_id')
		local_date = self.get_local_date(self.date_order)

		for user_id in user_ids:
			mail = self.env.ref('equip3_manuf_sale.sale_order_auto_mail_template')
			mail.partner_to = str(user_id.partner_id.id)
			mail.lang = user_id.partner_id.lang
			mail.body_html = f"""
			<p>Dear {user_id.name},</p>
			<p>Administrator has approved the Sales Order ({self.name}) on {local_date}</p>
			{self.get_mrp_button()}
			<p>Best Regards.</p>
			"""

			mail.send_mail(self.id, force_send=True)
			_logger.info(f'Mail has been sent to {user_id.name} on {local_date}')

	def _send_system_notification(self):
		user_ids = self.env['mrp.notification'].search([('type', '=', 'system')]).mapped('receiver_ids').mapped('user_id')
		local_date = self.get_local_date(self.date_order)

		for user_id in user_ids:
			mail_message_id = self.env['mail.message'].create({
				'email_from': self.env.user.email_formatted,
				'author_id': self.env.user.partner_id.id,
				'message_type': 'email',
				'is_internal': True,
				'body': f"""<p>Dear {user_id.partner_id.name},</p>
				<p>Administrator has approved the Sales Order ({self.name}) on {local_date}</p>
				{self.get_mrp_button()}
				<p style="margin:16px 0px 16px 0px">Best Regards.</p>
				"""
			})

			mail_notif = self.env['mail.notification'].create({
				'mail_message_id': mail_message_id.id,
				'notification_type': 'inbox',
				'res_partner_id': user_id.partner_id.id
			})

	def _send_whatsapp_notification(self):
		user_ids = self.env['mrp.notification'].search([('type', '=', 'whatsapp')]).mapped('receiver_ids').mapped('user_id')
		local_date = self.get_local_date(self.date_order)

		for user in user_ids:
			message = f"""
			Dear {user.name},
			{self.env.user.partner_id.name} has confirmed the Sales Order ({self.name}) on {local_date} which auto created the Manufacturing Plan/Manufacturing Order {self.get_mrp_plan_link(self.mrp_plan_ids.id)} / {self.get_mrp_link(self.mrp_order_ids.id)}
			Best Regards.
			"""
			if user.partner_id.mobile:
				phone_num = str(user.partner_id.mobile)
				if "+" in phone_num:
					phone_num =  phone_num.replace("+","")
				param = {'body': message, 'phone': phone_num}
				self.ca_request('post','sendMessage',param)

	def get_mrp_link(self, rec_id):
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		return '%s/web#id=%s&model=mrp.production&view_type=form' % (base_url, rec_id)

	def get_mrp_plan_link(self, rec_id):
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		if rec_id:
			return '%s/web#id=%s&model=mrp.plan&view_type=form' % (base_url, rec_id)
		else:
			return False
	
	def ca_get_endpoint(self, resource_path):
		api_key = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
		end_point = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
		return '%s/%s?token=%s' % (end_point.strip('/'), resource_path, api_key)
	
	def ca_request(self, req_type, path, param={}, timeout=False):
		def response_handle_error(req):
			error = False
			try:
				ret = req.json()
			except ValueError as _e:
				ret = {}
			err = ret.get('error', 'Send Error')
			message = ret.get('message', 'Send Error')
			if req.status_code == 401:
				error = err
			elif not 200 <= req.status_code <= 299:
				error = err or message
			if error:
				log_request_error([error, req_type, path, param], req)
				raise ValidationError(error)
			return ret
		self.ensure_one()
		result = {}
		timeout = timeout or TIMEOUT
		url = self.ca_get_endpoint(path)
		header = {'Accept': 'application/json'}
		req = False
		try:
			if req_type == 'post':
				data = json.dumps(param)
				header.update({'Content-Type': 'application/json'})
				w = len(data) / 20000
				timeout = (int(max(10, w)), 20)
				req = requests.post(url, data=data, headers=header, timeout=timeout, verify=True)
				result = response_handle_error(req)
		except requests.exceptions.SSLError as _err:
			log_request_error(['SSLError', req_type, path, param])
			raise UserError(_('Error! Could not connect to Chat-Api server. '
								'Please in the connector settings, set the '
								'parameter "Verify" to false by unchecking it and try again.'))
		except requests.exceptions.ConnectTimeout as _err:
			log_request_error(['ConnectTimeout', req_type, path, param])
			raise UserError(_('Timeout error. Try again...'))
		except (requests.exceptions.HTTPError,
				requests.exceptions.RequestException,
				requests.exceptions.ConnectionError) as _err:
			log_request_error(['requests', req_type, path, param])
			ex_type, _ex_value, _ex_traceback = sys.exc_info()
			raise UserError(_('Error! Could not connect to Chat-Api account.\n%s') % ex_type)
		return result		
			
	""" Need to move  `action_confirm` to `_action_confirm` 
	because there's a chance `action_confirm` doesn't called when confirming SO.
	See changes on equip3_sale modules. """
	def _action_confirm(self):
		res = super(SaleOrder, self)._action_confirm()
		company = self.env.company
		if not company.sales_to_manufacturing:
			return res

		for sale in self:
			sale._check_for_manufacturing_plan_orders()
			if company.send_email_so_confirm:
				sale._send_email_notification()
			if company.send_system_so_confirm:
				sale._send_system_notification()
			# if company.send_whatsapp_so_confirm:
			# 	sale._send_whatsapp_notification()
		return res

	def action_view_manufacturing(self):
		if self.mrp_order_ids or self.mrp_plan_ids:
			model = self.env.context.get('model')
			name = model == 'mrp.production' and 'Manufacturing Order' or "Manufacturing Plan"
			mrp_ids = model == 'mrp.production' and self.mrp_order_ids or self.mrp_plan_ids
			
			action = {
				'name': name,
				'type': 'ir.actions.act_window',
				'res_model': model,
				'target': 'current'
			}
			if len(mrp_ids) == 1:
				action.update({
					'view_mode': 'form',
					'res_id': mrp_ids[0].id
				})
			else:
				action.update({
					'view_mode': 'tree,form',
					'domain': [('sale_order_id', '=', self.id)]
				})

			return action


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	# branch_id should be moved to equip3_sale
	branch_id = fields.Many2one('res.branch', string='Branch', related='order_id.branch_id')

	bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', domain="""[
		'&',
			'|',
				('branch_id', '=', False),
				('branch_id', '=', branch_id),
			'|',
				('company_id', '=', False),
				('company_id', '=', company_id),
			'&',
				'|',
					('product_id', '=', product_id),
					'&',
						('product_tmpl_id.product_variant_ids', '=', product_id),
						('product_id', '=', False),
		('type', '=', 'normal')]""")

	manuf_auto_create = fields.Selection(related='product_id.manuf_auto_create')

	@api.onchange('product_id')
	def _pick_bom_from_product(self):
		if not self.product_id:
			return
		bom = self.env['mrp.bom']._bom_find(product=self.product_id, company_id=self.company_id.id, bom_type='normal')
		self.bom_id = bom and bom.id or False
