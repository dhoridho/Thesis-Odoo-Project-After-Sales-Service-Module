# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging


class SaleOrderReport(models.AbstractModel):
    _name = 'report.equip3_construction_sales_operation.sale_order_const'
    _description = 'Sale Order Construction Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order.const'].browse([data['sale_order_id']])
        return {
            'doc_ids': self.ids,
            'doc_model': 'construction.sale.order.report.wizard',
            'docs': docs,
            'scope_sect_prod_dict': data['scope_sect_prod_dict'],
            'print_contract_letter': data['print_contract_letter'],
            'print_level_option': data['print_level_option'],
            'is_rounding': data['is_rounding'],
        }
