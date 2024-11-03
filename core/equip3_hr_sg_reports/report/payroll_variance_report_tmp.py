import time

from odoo import api, models


class PayrollSummaryReport(models.AbstractModel):
    _name = 'report.equip3_hr_sg_reports.payroll_variance_report_tmp'
    _description = "Payroll Variance Report"

    def _get_report_values(self, docids, data=None):
        ctx = self.env.context
        model = ctx.get('active_model', 'payroll.variance.report')
        docs = self.env[model].browse(ctx.get('active_id', docids))
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
            }
