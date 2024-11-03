# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning



class StockPicking(models.Model):
	_inherit = "stock.picking"

	sale_ids = fields.Many2many('sale.order',string = 'sale references')
	purchase_ids = fields.Many2many('purchase.order',string = 'Purchase references')

			
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
