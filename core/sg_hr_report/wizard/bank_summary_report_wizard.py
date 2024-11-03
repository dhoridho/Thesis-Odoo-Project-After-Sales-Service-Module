
import base64
import io

import locale
import time
from datetime import datetime
from odoo.tools.misc import formatLang, format_date, get_lang

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import ValidationError

import xlwt


class ExcelExportSummary(models.TransientModel):
    _name = "excel.export.summary"
    _description = "Excel Export Summary"

    file = fields.Binary("Click On Download Link To Download Xls File",
                         readonly=True)
    name = fields.Char("Name", default='Bank_summary.xls')


class ViewBankSummaryReportWizard(models.TransientModel):
    _name = 'view.bank.summary.report.wizard'
    _description = "View Bank Summary Report"

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_bank_rel_tbl',
                                    'rel_bank_id', 'rel_employee_id',
                                    'Employee Name')
    start_date = fields.Date('Start Date',
                             default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=lambda *a: str(datetime.now() +
                                                  relativedelta(months=+1,
                                                                day=1,
                                                                days=-1))[:10])
    export_report = fields.Selection([('pdf', 'PDF'),
                                      ('excel', 'Excel')],
                                     "Export", default='pdf')

    def print_bank_summary_report(self):
        """Print bank summary report.

        The method used to call download of wizard action called or
        Bank Summary Report of Template called If selected PDF or Excel
        Type of Report.
        @self : Record Set
        @return : The return wizard of action in dictionary
        ----------------------------------------------------------------
        """
        context = self.env.context
        payslip_line_obj = self.env['hr.payslip.line']
        data = self.read([])[0]
        if not self.employee_ids.ids:
            raise ValidationError(_("Please select employee"))
        if self.start_date >= self.end_date:
            raise ValidationError(_('You must be enter start date less than '
                                    'end date !'))
        for employee in self.employee_ids:
            if not employee.bank_account_id:
                raise ValidationError(_('There is no Bank Account define '
                                        'for %s employee.' % (employee.name)))
        payslip_line_ids = payslip_line_obj.search([
            ('slip_id.employee_id', 'in', self.employee_ids.ids),
            ('slip_id.date_from', '>=', self.start_date),
            ('slip_id.date_from', '<=', self.end_date),
            ('slip_id.pay_by_cheque', '=', False),
            ('code', '=', 'NET'),
            ('slip_id.state', 'in', ['draft', 'done', 'verify'])])

        if not payslip_line_ids.ids:
            raise ValidationError(_('There is no payslip details available for'
                                    ' bank between selected date %s and %s')
                                  % (self.start_date.strftime(get_lang(self.env).date_format),
                                    self.end_date.strftime(get_lang(self.env).date_format)))

        dept_dict = {}
        for line in payslip_line_ids:
            emp = line.slip_id.employee_id.name
            empl = line.slip_id.employee_id
            dept = empl.department_id.name
            bank = empl.bank_account_id
            emp_vals = {
                'amount': line.total,
                'login': empl.user_id and empl.user_id.login or '',
                'bank_name': bank and bank.bank_name,
                'bank_code': bank and bank.bank_id and bank.bank_id.bic,
                'acc_number': bank.acc_number,
                'branch': bank.branch_id
            }
            if dept and dept not in dept_dict.keys():
                dept_dict[dept] = {emp: emp_vals}
            elif dept and dept in dept_dict.keys():
                if emp in dept_dict[dept]:
                    dept_dict[dept][emp]['amount'] += line.total
                else:
                    dept_dict[dept].update({emp: emp_vals})
            elif not dept and 'Undefined' not in dept_dict.keys():
                dept_dict['Undefined'] = {emp: emp_vals}
            elif not dept and 'Undefined' in dept_dict.keys():
                if emp in dept_dict['Undefined']:
                    dept_dict['Undefined'][emp]['amount'] += line.total
                else:
                    dept_dict['Undefined'].update({emp: emp_vals})
        res_user = self.env.user
        if self.export_report == "pdf":
            datas = {
                'ids': self.ids,
                'model': self._name,
                'form': data,
                'dept_dict': dept_dict,
            }
            report_id = self.env.ref('sg_hr_report.hr_bank_summary_report')
            return report_id.report_action(
                self, data=datas)

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        font = xlwt.Font()
        font.bold = True
        header = xlwt.easyxf('font: bold 1, height 280')
        start_date_formate = self.start_date.strftime('%d/%m/%Y')
        end_date_formate = self.end_date.strftime('%d/%m/%Y')
        start_date_to_end_date = tools.ustr(start_date_formate) + ' To ' \
            + tools.ustr(end_date_formate)
        worksheet.col(0).width = 5000
        worksheet.col(1).width = 5000
        worksheet.row(0).height = 500
        worksheet.row(1).height = 500
        worksheet.write(0, 0, "Company Name", header)
        worksheet.write(0, 1, res_user.company_id.name, header)
        worksheet.write(0, 7, "By Bank", header)
        worksheet.write(1, 0, "Period", header)
        worksheet.write(1, 1, start_date_to_end_date, header)
        worksheet.col(9).width = 5000
        worksheet.col(11).width = 5000
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
        row = 4
        for dept in dept_dict:
            worksheet.write(row, 0, "", border_style)
            worksheet.write(row, 1, "Employee Name", border_style)
            worksheet.write(row, 2, "", border_style)
            worksheet.write(row, 3, "Employee Login", border_style)
            worksheet.write(row, 4, "", border_style)
            worksheet.write(row, 5, "Amount", border_style)
            worksheet.write(row, 6, "", border_style)
            worksheet.write(row, 7, "Name Of Bank", border_style)
            worksheet.write(row, 8, "", border_style)
            worksheet.write(row, 9, "Bank Code", border_style)
            worksheet.write(row, 10, "", border_style)
            worksheet.write(row, 11, "Account Number", border_style)
            worksheet.write(row, 12, "", border_style)
            worksheet.write(row, 13, "Branch Code", border_style)
            row += 1

            dept_total = 0
            for employee in dept_dict[dept]:
                emp = dept_dict[dept][employee]
                net_total = '%.2f' % emp['amount']
                dept_total += emp['amount']
                worksheet.write(row, 1, employee)
                worksheet.write(row, 2, "")
                worksheet.write(row, 3, emp['login'] or '')
                worksheet.write(row, 4, "")
                worksheet.write(row, 5,
                                res_user.company_id.currency_id.symbol +
                                ' ' +
                                tools.ustr(locale.format("%.2f",
                                                         float(net_total),
                                                         grouping=True)))
                worksheet.write(row, 6, "")
                worksheet.write(row, 7, emp['bank_name'] or '')
                worksheet.write(row, 8, "")
                worksheet.write(row, 9, emp['bank_code'] or '')
                worksheet.write(row, 10, "")
                worksheet.write(row, 11, emp['acc_number'] or '')
                worksheet.write(row, 12, "")
                worksheet.write(row, 13, emp['branch'] or '')
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
            worksheet.write(row, 8, '', border_style)
            worksheet.write(row, 9, '', border_style)
            worksheet.write(row, 10, '', border_style)
            worksheet.write(row, 11, '', border_style)
            worksheet.write(row, 12, '', border_style)
            worksheet.write(row, 13, '', border_style)
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
            dept_total = sum([dept_dict[dept][employee]['amount']
                              for employee in dept_dict[dept]])
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

        excelfile = io.BytesIO()
        workbook.save(excelfile)
        excelfile.seek(0)
        data = excelfile.read()
        excelfile.close()
        res = base64.b64encode(data)
        vals = {'name': 'Bank Summary.xls', 'file': res}
        module_rec = self.env['excel.export.summary'].create(vals)
        return {'name': _('Bank Summary Report'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'excel.export.summary',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}
