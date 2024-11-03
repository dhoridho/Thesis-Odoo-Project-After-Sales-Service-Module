# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HrBcaBankTransferAttachment(models.TransientModel):
    _name = "hr.payroll.report.attachment"
    _description = "HR Payroll Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')

class HrPayrollReport(models.TransientModel):
    _name = 'hr.payroll.report'

    def _compute_year_selection(self):
        year_list = []
        current_year = int(time.strftime('%Y'))

        year_range = range(2015, current_year + 1)
        for year in reversed(year_range):
            year_list.append((str(year), str(year)))
        return year_list

    def _compute_month_selection(self):
        month_list = []
        for x in range(1, 13):
            month_list.append((str(calendar.month_name[x]), str(calendar.month_name[x])))
        return month_list
    
    @api.model
    def _employee_domain(self):
        domain =  [('company_id','=',self.env.company.id)]
        return domain

    year = fields.Selection(selection=lambda self: self._compute_year_selection(), string="Year", default="none",
                            required=True)
    month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", default="none",
                             required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
        ('refund', 'Refund')
    ], string='Status', required=True, default='')
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True,domain=_employee_domain)

    def action_print_excel(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        company_name = self.env.company.name

        salary_rule = self.env['hr.salary.rule'].sudo().search([('appears_on_report', '=', True)], order='sequence ASC')
        rules = []
        col_no = 7
        for item in salary_rule:
            row = [None, None, None]
            row[0] = col_no
            row[1] = item.code
            row[2] = item.name
            rules.append(row)
            col_no += 1

        month_datetime = datetime.strptime(self.month, "%B")
        selected_month_number = month_datetime.month
        last_day_month = calendar.monthrange(int(self.year), selected_month_number)[1]
        month_selected = str('{:02d}'.format(selected_month_number))
        selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
        selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
        selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
        selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

        payroll_period = str(month_datetime.strftime("%b")) + ' ' + str(self.year)

        file_name = 'Payroll Report ' + payroll_period + '.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        format1 = xlwt.easyxf('font:height 200,bold True; align: horiz left;')
        format2 = xlwt.easyxf('font:height 200; align: horiz left;')
        format3 = xlwt.easyxf('font:height 200, bold True; align: horiz center;')
        format4 = xlwt.easyxf('font:height 200; align: horiz center;')
        format5 = xlwt.easyxf('font:height 200; align: horiz right;')
        sheet = workbook.add_sheet('Payroll Report')
        sheet.col(0).width = int(25 * 200)
        sheet.col(1).width = int(25 * 200)
        sheet.col(2).width = int(25 * 200)
        sheet.col(3).width = int(25 * 200)
        sheet.col(4).width = int(25 * 200)
        sheet.col(5).width = int(25 * 200)
        sheet.col(6).width = int(25 * 200)
        for rule in rules:
            sheet.col(rule[0]).width = int(25 * 300)
        sheet.write(0, 0, "Company", format1)
        sheet.write(0, 1, company_name, format2)
        sheet.write(1, 0, "Period", format1)
        sheet.write(1, 1, payroll_period, format2)
        sheet.write(3, 0, "Employee", format3)
        sheet.write(3, 1, "Employee ID", format3)
        sheet.write(3, 2, "Job Position", format3)
        sheet.write(3, 3, "Department", format3)
        sheet.write(3, 4, "Contract", format3)
        sheet.write(3, 5, "Contract Type", format3)
        sheet.write(3, 6, "Work Location", format3)
        for rule in rules:
            sheet.write(3, rule[0], rule[2], format3)

        row_x = 4
        row_y = 4
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', self.state),
                                                      ('payslip_report_date', '>=', selected_month_start_date),
                                                      ('payslip_report_date', '<=', selected_month_end_date),
                                                      ('payslip_pesangon', '=', False)])

            employee_name = emp.name
            employee_id = emp.sequence_code
            contract_obj = self.env['hr.contract'].search(
                [('employee_id', '=', emp.id), ('state', '=', 'open')], limit=1)
            contract = contract_obj.name if contract_obj and contract_obj.name else ''
            contract_type = contract_obj.type_id.name if contract_obj and contract_obj.type_id else ''
            work_location = emp.location_id.name if emp.location_id else ''

            if payslips:
                job_position = payslips.job_id.name if payslips.job_id else ''
                department = payslips.department_id.name if payslips.department_id else ''
                sheet.write(row_x, 0, employee_name, format2)
                sheet.write(row_x, 1, employee_id, format4)
                sheet.write(row_x, 2, job_position, format2)
                sheet.write(row_x, 3, department, format2)
                sheet.write(row_x, 4, contract, format2)
                sheet.write(row_x, 5, contract_type, format2)
                sheet.write(row_x, 6, work_location, format2)
                for line in payslips.line_ids:
                    for rule in rules:
                        if line.code == rule[1]:
                            if line.amount > 0:
                                sheet.write(row_y, rule[0], "{:0,.2f}".format(line.amount), format5)
                row_x += 1
                row_y += 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['hr.payroll.report.attachment'].create(
            {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'name': 'Payroll Report',
            'res_model': 'hr.payroll.report.attachment',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

