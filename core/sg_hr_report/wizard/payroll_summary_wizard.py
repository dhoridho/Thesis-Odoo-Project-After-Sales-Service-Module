
import time
from datetime import datetime
from odoo.tools.misc import formatLang, format_date, get_lang

from dateutil.relativedelta import relativedelta as rv

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import ValidationError


class PayrollSummaryWizard(models.TransientModel):
    _name = 'payroll.summary.wizard'
    _description = "Payroll Summary"

    date_from = fields.Date('Date From',
                            default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date('Date To',
                          default=lambda *a: str(datetime.now() +
                                                 rv(months=+1, day=1,
                                                    days=-1))[:10])
    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employee_payroll_rel', 'emp_id3', 'employee_id',
        'Employee Name')
    company_id = fields.Many2one('res.company', 'Company', index=True,
                                 default=lambda self: self.env.user.company_id)

    def print_order(self):
        """Print the order.

        The method used to HR Payroll Summary Report of Template called.
        @self: Record set
        @return: Return action of wizard in dictionary
        -------------------------------------------------------------------------
        """
        emp_ids = self.employee_ids
        date_from = self.date_from
        date_to = self.date_to
        if not self.employee_ids.ids:
            raise ValidationError(_("Please select employee"))
        res_user = self.env.user
        if self.date_from >= self.date_to:
            raise ValidationError(_(
                "You must be enter start date less than end date !"))
        payslip_ids = self.env['hr.payslip'].search([
            ('employee_id', 'in', emp_ids.ids),
            ('date_from', '>=', date_from),
            ('date_from', '<=', date_to),
            ('state', 'in', ['draft', 'done', 'verify'])], limit=1)
        if not payslip_ids.ids:
            raise ValidationError(_(
                'There is no payslip details available between '
                'selected date %s and %s') % (
                    date_from.strftime(get_lang(self.env).date_format),
                    date_to.strftime(get_lang(self.env).date_format)))
        data = self.read()[0]
        data.update({'currency':
                     " " + tools.ustr(res_user.company_id.currency_id.symbol),
                     'company': res_user.company_id.name})
        report_id = self.env.ref('sg_hr_report.hr_employee_payroll_summary')
        return report_id.report_action(self, data=data, config=False)
