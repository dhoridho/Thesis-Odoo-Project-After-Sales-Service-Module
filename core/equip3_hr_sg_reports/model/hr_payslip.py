import babel
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from datetime import datetime, time


class Equip3SgHrPayslip(models.Model):
    _inherit = "hr.payslip"

    report_file_name = fields.Char(
        string='Report File Name',
        compute='_get_report_file_name'
    )

    def action_payslip_done(self):
        payslips = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', self.date_from),
            ('date_from', '<=', self.date_to),
            ('state', '=', 'done')
        ])
        if payslips:
            raise ValidationError(_(
                "Payslip on selected date %s to %s has been generated." % (
                    self.date_from, self.date_to
                )
            ))
        return super(Equip3SgHrPayslip, self).action_payslip_done()

    @api.depends('employee_id', 'date_from', 'date_to')
    def _get_report_file_name(self):
        if self.employee_id and self.date_from and self.date_to:
            employee = self.employee_id
            date_from = self.date_from
            ttyme = datetime.combine(
                fields.Date.from_string(date_from), time.min
            )
            locale = self.env.context.get('lang') or 'en_US'

            self.report_file_name = _('Payslip %s for %s') % (
                employee.name, tools.ustr(babel.dates.format_date(
                    date=ttyme, format='MMMM y', locale=locale
                ))
            )
