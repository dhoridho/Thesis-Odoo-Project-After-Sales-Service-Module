# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models
from datetime import datetime


class ProbationReport(models.AbstractModel):
    _name = 'report.dev_employee_probation.probation_template'

    def date_conversion(self, base_date):
        final_date = base_date
        if base_date:
            final_date = datetime.strptime(str(base_date), "%Y-%m-%d").strftime('%d-%m-%Y')
        return final_date

    def get_performance(self, probation_id):
        performance = ''
        if probation_id.performance == 'excellent':
            performance = 'Excellent'
        if probation_id.performance == 'good':
            performance = 'Good'
        if probation_id.performance == 'average':
            performance = 'Average'
        if probation_id.performance == 'poor':
            performance = 'Poor'
        if probation_id.performance == 'worst':
            performance = 'Worst'
        return performance

    def _get_report_values(self, docids, data=None):
        docs = self.env['employee.probation'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'employee.probation',
            'docs': docs,
            'date_conversion': self.date_conversion,
            'get_performance': self.get_performance,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: