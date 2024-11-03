# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime,date, timedelta


class InheritStockMoveLine(models.Model):
	_inherit = 'stock.move.line'

	move_remarks_line = fields.Char('Remarks')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
