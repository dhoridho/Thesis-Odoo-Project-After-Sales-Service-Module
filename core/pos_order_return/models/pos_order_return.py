# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from odoo.tools.translate import _
from odoo.tools import float_is_zero
from odoo import api, fields, models
from odoo.exceptions import UserError, Warning
import psycopg2

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	not_returnable = fields.Boolean('Not Returnable')

class PosOrder(models.Model):
	_inherit = 'pos.order'

	is_return_order = fields.Boolean(string='Return Order',copy=False)
	return_order_id = fields.Many2one('pos.order','Return Order Of',readonly=True,copy=False)
	return_status = fields.Selection([('-','Not Returned'),('Fully-Returned','Fully-Returned'),('Partially-Returned','Partially-Returned'),('Non-Returnable','Non-Returnable')],default='-',copy=False,string='Return Status')

	@api.model
	def _process_order(self, order, draft, existing_order):
	#-------- for order return code start-----------------
		# data = order.get('data')
		# if data.get('is_return_order'):
		# 	data['amount_paid'] = 0
		# 	for line in data.get('lines'):
		# 		line_dict = line[2]
		# 		line_dict['qty'] = line_dict['qty']
		# 		if line_dict.get('original_line_id'):
		# 			original_line = self.env['pos.order.line'].browse(line_dict.get('original_line_id'))
		# 			original_line.line_qty_returned += abs(line_dict['qty'])
		# 	for statement in data.get('statement_ids'):
		# 		statement_dict = statement[2]
		# 		if data['amount_total'] <0:
		# 			statement_dict['amount'] = statement_dict['amount'] * -1
		# 		else:
		# 			statement_dict['amount'] = statement_dict['amount']
		# 	if data['amount_total'] <0:
		# 		data['amount_tax'] = data.get('amount_tax')
		# 		data['amount_return'] = 0
		# 		data['amount_total'] = data.get('amount_total')
	#----------  for order return code end  --------
		res = super(PosOrder,self)._process_order(order,draft, existing_order)
		return res

	@api.model
	def _order_fields(self,ui_order):
		fields_return = super(PosOrder,self)._order_fields(ui_order)
		fields_return.update({
			'is_return_order':ui_order.get('is_return_order') or False,
			'return_order_id':ui_order.get('return_order_id') or False,
			'return_status':ui_order.get('return_status') or False,
			})
		return fields_return


class PosOrderLine(models.Model):
	_inherit = 'pos.order.line'
	line_qty_returned = fields.Integer('Line Returned', default=0)
	original_line_id = fields.Many2one('pos.order.line', "Original line")

	@api.model
	def _order_line_fields(self,line,session_id=None):
		fields_return = super(PosOrderLine,self)._order_line_fields(line,session_id)
		fields_return[2].update({'line_qty_returned':line[2].get('line_qty_returned','')})
		fields_return[2].update({'original_line_id':line[2].get('original_line_id','')})
		return fields_return
