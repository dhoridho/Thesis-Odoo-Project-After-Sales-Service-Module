import time

from odoo import api, models


class PpdBankSummaryReceipt(models.AbstractModel):
    _name = 'report.sg_hr_report.hr_bank_summary_report_tmp'
    _description = "Bank Summary Receipt"

    @api.model
    def get_total(self, data):
        """Get the total."""
        grand_total = 0.0
        for dept in data:
            grand_total += sum(
                [data[dept][emp]['amount'] for emp in data[dept]])
        return grand_total

    @api.model
    def get_total_emp(self, data):
        """Get the total record."""
        emp_list = []
        for dept in data:
            emp_list.append(data[dept])
        return len(emp_list)

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values."""
        model = self.env.context.get(
            'active_model', 'view.bank.summary.report.wizard')
        docs = self.env[model].browse(
            self.env.context.get('active_id', docids))

        dept_dict = data.get('dept_dict')
        total_employees = self.get_total_emp(dept_dict)
        total = self.get_total(dept_dict)
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
                'time': time,
                'get_info': dept_dict,
                'get_totalrecord': total_employees,
                'get_total': total}
