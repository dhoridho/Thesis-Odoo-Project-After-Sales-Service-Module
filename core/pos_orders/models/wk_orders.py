    # -*- coding: utf-8 -*-
    #################################################################################
    #
    #   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
    #   See LICENSE file for full copyright and licensing details.
    #   License URL : <https://store.webkul.com/license.html/>
    # 
    #################################################################################
from odoo import api, fields, models
from odoo.exceptions import Warning,ValidationError
import logging
_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
	_inherit = 'pos.order'


	ean13 = fields.Char('Ean13', readonly=1)

	@api.model
	def create_from_ui(self, orders, draft=False):
		order_ids = super(PosOrder, self).create_from_ui(orders,draft)
		for order_id in order_ids:
			order_list = []
			order_line_list = []
			payment_list = []
			if(order_id.get('id')):
				order = self.browse([order_id.get('id')])
				vals = {}
				vals['lines'] = []
				if hasattr(order[0], 'return_status'):
					if not order.is_return_order:
						vals['return_status'] = order.return_status
						vals['existing'] = False
						vals['id'] = order.id
					else:
						order.return_order_id.return_status = order.return_status
						vals['existing'] = True
						vals['id'] = order.id
						vals['original_order_id'] = order.return_order_id.id
						vals['return_status'] = order.return_order_id.return_status
						for line in order.lines:
							line_vals = {}
							if line.original_line_id:
								line_vals['id'] = line.original_line_id.id
								line_vals['line_qty_returned'] = line.original_line_id.line_qty_returned
								line_vals['existing'] = True
							order_line_list.append(line_vals)
				vals['statment_ids'] = [obj.payment_method_id for obj in order.payment_ids]
				vals['name'] = order.name
				vals['amount_total'] = order.amount_total
				vals['pos_reference'] = order.pos_reference
				vals['state'] = order.state
				vals['session_id'] = order.session_id.id
				vals['date_order'] = order.date_order
				if order.account_move:
					vals['invoice_id'] = order.account_move.id
				else:
					vals['invoice_id'] = False
				if order.partner_id:
					vals['partner_id'] = [order.partner_id.id, order.partner_id.name]
				else:
					vals['partner_id'] = False
				if (not hasattr(order[0], 'return_status') or (hasattr(order[0], 'return_status') and not order.is_return_order)):
					vals['id'] = order.id
					for line in order.lines:
						vals['lines'].append(line.id)
						line_vals = {}
						# LINE DATAA
						line_vals['create_date'] = line.create_date
						line_vals['discount'] = line.discount
						line_vals['display_name'] = line.display_name
						line_vals['id'] = line.id
						line_vals['order_id'] = [line.order_id.id, line.order_id.name]
						line_vals['price_subtotal'] = line.price_subtotal
						line_vals['price_subtotal_incl'] = line.price_subtotal_incl
						line_vals['price_unit'] = line.price_unit
						line_vals['product_id'] = [line.product_id.id, line.product_id.name]
						line_vals['qty'] = line.qty
						line_vals['write_date'] = line.write_date
						if hasattr(line, 'line_qty_returned'):
							line_vals['line_qty_returned'] = line.line_qty_returned
						# LINE DATAA
						order_line_list.append(line_vals)
					for payment_id in order.payment_ids:
						payment_vals = {}
						# STATEMENT DATAA
						payment_vals['amount'] = payment_id.amount
						payment_vals['id'] = payment_id.id
						if payment_id.payment_method_id:
							currency = payment_id.payment_method_id.company_id.currency_id
							payment_vals['journal_id'] = [payment_id.payment_method_id.id, payment_id.payment_method_id.name + " (" +currency.name+")"]
						else:
							payment_vals['journal_id'] = False
						payment_list.append(payment_vals)
				order_list.append(vals)
			order_id['orders'] = order_list
			order_id['orderlines'] = order_line_list
			order_id['payments'] = payment_list

		return order_ids

class PosConfig(models.Model):
	_inherit = 'pos.config'

	order_loading_options = fields.Selection([("current_session","Load Orders Of Current Session"), ("all_orders","Load All Past Orders"), ("n_days","Load Orders Of Last 'n' Days")], default='current_session', string="Loading Options")
	number_of_days = fields.Integer(string='Number Of Past Days',default=10)

	@api.constrains('number_of_days')
	def number_of_days_validation(self):
		if self.order_loading_options == 'n_days':
			if not self.number_of_days or self.number_of_days < 0:
				raise ValidationError("Please provide a valid value for the field 'Number Of Past Days'!!!")
