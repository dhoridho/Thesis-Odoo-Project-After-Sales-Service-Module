
import base64
import io
import locale
import time
from datetime import datetime
from odoo.tools.misc import formatLang, format_date, get_lang

from dateutil.relativedelta import relativedelta as rv

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import ValidationError

import xlwt


class ExcelExportChequeSummary(models.TransientModel):
    _name = "excel.export.cheque.summary"
    _description = "Excel Export Cheque Summary Report"

    file = fields.Binary("Click On Download Link To Download Xls File",
                         readonly=True)
    name = fields.Char("Name", default='Cheque_summary.xls')


class ViewChequeSummaryReportWizard(models.TransientModel):
    _name = 'view.cheque.summary.report.wizard'
    _description = "View Cheque Summary Report"

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_cheque_rel',
                                    'emp_id', 'employee_id', 'Employee Name')
    export_report = fields.Selection([('pdf', 'PDF'),
                                      ('excel', 'Excel')], "Export",
                                     default='pdf')
    date_start = fields.Date('Date Start',
                             default=lambda *a: time.strftime('%Y-%m-01'))
    date_stop = fields.Date('Date End',
                            default=lambda *a: str(datetime.now() +
                                                   rv(months=+1, day=1,
                                                      days=-1))[:10])

    def print_cheque_summary_report(self):
        """Print the checque summary report.

        The method used to call download of wizard action called or
        Cheque Summery Report of Template called If selected PDF or Excel
        Type of Report.
        @self : Record Set
        @return : The return wizard of action in dictionary
        ----------------------------------------------------------------
        """
        data = self.read([])[0]
        context = self.env.context
        if not self.employee_ids.ids:
            raise ValidationError(_("Please select employee"))
        if self.date_start >= self.date_stop:
            raise ValidationError(_(
                'You must be enter start date less than '
                'end date !'))
        for employee in self.employee_ids:
            if not employee.bank_account_id:
                raise ValidationError(_('There is no Bank Account define for %s employee.' % (employee.name)))
        payslip_line_obj = self.env['hr.payslip.line']
        payslip_line_ids = payslip_line_obj.search([
            ('slip_id.employee_id', 'in', self.employee_ids.ids),
            ('slip_id.date_from', '>=', self.date_start),
            ('slip_id.date_from', '<=', self.date_stop),
            ('slip_id.pay_by_cheque', '=', True),
            ('code', '=', 'NET'),
            ('slip_id.state', 'in', ['draft', 'done', 'verify'])])

        if not payslip_line_ids.ids:
            raise ValidationError(_(
                'There is no payslip details available '
                'for cheque payment between selected date '
                '%s and %s!' % (self.date_start.strftime(get_lang(self.env).date_format),
                    self.date_stop.strftime(get_lang(self.env).date_format))))
        dept_dict = {}
        for line in payslip_line_ids:
            emp = line.slip_id.employee_id.name
            empl = line.slip_id.employee_id
            dept = empl.department_id.name
            emp_vals = {
                'amount': line.total,
                'login': empl.user_id and empl.user_id.login or '',
                'cheque_number': line.slip_id.cheque_number,
                'emp_name': empl.name,
            }
            if dept and dept not in dept_dict.keys():
                dept_dict[dept] = {line.slip_id.number: emp_vals}
            elif dept and dept in dept_dict.keys():
                dept_dict[dept].update({line.slip_id.number: emp_vals})
            elif not dept and 'Undefined' not in dept_dict.keys():
                dept_dict['Undefined'] = {line.slip_id.number: emp_vals}
            elif not dept and 'Undefined' in dept_dict.keys():
                dept_dict['Undefined'].update({line.slip_id.number: emp_vals})
        res_user = self.env.user
        symbol = res_user.company_id.currency_id.symbol
        if self.export_report == "pdf":
            data.update({
                'currency': " " + tools.ustr(symbol),
                'company': res_user.company_id.name})
            datas = {
                'ids': self.ids,
                'model': self._name,
                'form': data,
                'dept_dict': dept_dict,
            }

            report_id = self.env.ref(
                'sg_hr_report.cheque_hr_summary_report')
            return report_id.report_action(
                self, data=datas, config=False)
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        font = xlwt.Font()
        font.bold = True
        header = xlwt.easyxf('font: bold 1, height 240;')
        res_user = self.env.user
        start_date_formate = self.date_start.strftime('%d/%m/%Y')
        end_date_formate = self.date_stop.strftime('%d/%m/%Y')
        start_date_to_end_date = (
            start_date_formate + ' to ' + end_date_formate)
        borders = xlwt.Borders()
        borders.top = xlwt.Borders.MEDIUM
        borders.bottom = xlwt.Borders.MEDIUM
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_CENTER
        alignment.vert = xlwt.Alignment.VERT_CENTER
        #  Create Style
        border_style = xlwt.XFStyle()
        border_style.alignment = alignment
        border_style.borders = borders
        #  Create Style
        alignment_style = xlwt.XFStyle()
        alignment_style.alignment = alignment
        right = xlwt.easyxf(
            'font: bold on;align: wrap off ,'
            ' vert center, horiz right;')

        worksheet.col(0).width = 7000
        worksheet.col(1).width = 5000
        worksheet.col(3).width = 5000
        worksheet.col(5).width = 5000
        worksheet.col(7).width = 5000
        worksheet.row(0).height = 500
        worksheet.row(1).height = 500
        worksheet.write(0, 0, "Company Name", header)
        worksheet.write(0, 1, res_user.company_id.name, header)
        worksheet.write(0, 7, "By Cheque", header)
        worksheet.write(1, 0, "Period", header)
        worksheet.write(1, 1, start_date_to_end_date, header)
        row = 2
        for dept in dept_dict:
            worksheet.write(row, 0, "", border_style)
            worksheet.write(row, 1, "Employee Name", border_style)
            worksheet.write(row, 2, "", border_style)
            worksheet.write(row, 3, "Employee Login", border_style)
            worksheet.write(row, 4, "", border_style)
            worksheet.write(row, 5, "Amount", border_style)
            worksheet.write(row, 6, "", border_style)
            worksheet.write(row, 7, "Cheque Number", border_style)
            row += 1
            dept_total = 0
            for emp in dept_dict[dept]:
                employee = dept_dict[dept][emp]
                net_total = employee['amount']
                worksheet.write(row, 0, "")
                worksheet.write(row, 1, employee['emp_name'] or '',
                                alignment_style)
                worksheet.write(row, 2, "")
                worksheet.write(row, 3, employee['login'] or '',
                                alignment_style)
                worksheet.write(row, 4, "")
                worksheet.write(row, 5,
                                symbol + ' ' +
                                tools.ustr(locale.format(
                                    "%.2f",
                                    float(net_total)), right))
                worksheet.write(row, 6, "")
                worksheet.write(row, 7, employee['cheque_number'] or '',
                                alignment_style)
                dept_total += net_total
                row += 1
            row += 1
            dept_total = '%.2f' % dept_total
            worksheet.write(row, 0, "Total " + dept, border_style)
            worksheet.write(row, 1, "", border_style)
            worksheet.write(row, 2, "", border_style)
            worksheet.write(row, 3, "", border_style)
            worksheet.write(row, 4, "", border_style)
            worksheet.write(
                row, 5,
                res_user.company_id.currency_id.symbol +
                ' ' + dept_total, border_style)
            worksheet.write(row, 6, '', border_style)
            worksheet.write(row, 7, '', border_style)
            row += 1
        row += 1
        worksheet.write(row, 0, 'Overall Total', border_style)
        worksheet.write(row, 1, '', border_style)
        worksheet.write(row, 2, '', border_style)
        row += 2
        grand_total = 0
        for dept in dept_dict:
            worksheet.write(row, 0, "Total " + dept)
            worksheet.write(row, 1, "")
            dept_total = sum([dept_dict[dept][emp]['amount']
                              for emp in dept_dict[dept]])
            grand_total += dept_total
            dept_total = '%.2f' % dept_total
            worksheet.write(
                row, 2,
                res_user.company_id.currency_id.symbol +
                ' ' + dept_total)
            row += 1
        row += 1
        worksheet.write(row, 0, "ALL")
        worksheet.write(row, 1, "")
        grand_total = '%.2f' % grand_total
        worksheet.write(
            row, 2,
            res_user.company_id.currency_id.symbol +
            ' ' + grand_total)
        excel_file = io.BytesIO()
        workbook.save(excel_file)
        excel_file.seek(0)
        data = excel_file.read()
        excel_file.close()
        res = base64.b64encode(data)
        vals = {'name': 'Cheque_summary.xls', 'file': res}
        module_rec = self.env['excel.export.cheque.summary'].create(vals)
        return {'name': _('Cheque Summary Report'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'excel.export.cheque.summary',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}
