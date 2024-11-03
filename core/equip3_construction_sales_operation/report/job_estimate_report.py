# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging


class BOQReport(models.AbstractModel):
    _name = 'report.equip3_construction_sales_operation.boq_report'
    _description = 'boq_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('equip3_construction_sales_operation.boq_report')
        docs = self.env['job.estimate'].browse([data['job_estimate_id']])
        return {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': docs,
            'data_rows': data['data_rows'],
            'print_level_option': data['print_level_option'],
        }
