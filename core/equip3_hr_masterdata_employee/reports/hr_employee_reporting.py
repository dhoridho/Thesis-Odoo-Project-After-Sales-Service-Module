# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api, _
from datetime import datetime

try:
    from statistics import stdev
except ImportError:
    import stdev

import xlwt
import base64
from io import BytesIO
from odoo.exceptions import ValidationError

class HrEmployeeReporting(models.TransientModel):
    _name = 'hr.employee.reporting'
    _description = "Employee Report"

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    department_ids = fields.Many2many('hr.department', string='Department', required=True, domain="[('company_id','=',company_id)]")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    def print_xls(self):
        if not self.department_ids:
            raise ValidationError(_('Please select department.'))

        company = self.company_id.name
        start = datetime.strptime(str(self.start_date), '%Y-%m-%d').strftime('%d/%m/%y')
        end = datetime.strptime(str(self.end_date), '%Y-%m-%d').strftime('%d/%m/%y')

        datas = []
        department_list = list()
        for dept in self.department_ids:
            department_list.append(dept.name)
            job_position = self.env['hr.job'].sudo().search([('department_id', '=', dept.id)])
            for position in job_position:
                employees = self.env['hr.employee'].sudo().search([('department_id', '=', dept.id), ('job_id', '=', position.id)])
                male_employees = self.env['hr.employee'].search_count([('department_id', '=', dept.id), ('job_id', '=', position.id), ('gender', '=', 'male')])
                female_employees = self.env['hr.employee'].search_count([('department_id', '=', dept.id), ('job_id', '=', position.id), ('gender', '=', 'female')])
                other_employees = self.env['hr.employee'].search_count([('department_id', '=', dept.id), ('job_id', '=', position.id), ('gender', '=', 'other')])
                employees_in = self.env['hr.employee'].search_count(
                    [('department_id', '=', dept.id), ('job_id', '=', position.id), ('date_of_joining', '>=', self.start_date),
                     ('date_of_joining', '<=', self.end_date)])
                employees_out = self.env['hr.contract'].search_count(
                    [('department_id', '=', dept.id), ('job_id', '=', position.id), ('date_end', '>=', self.start_date),
                     ('date_end', '<=', self.end_date)])
                sum_age = 0
                sum_salary = 0
                avg_age = 0
                avg_salary = 0
                list_salary = list()
                lowest_salary = 0
                highest_salary = 0
                standard_deviation = 0
                low_average_salary = 0
                high_average_salary = 0
                for employee in employees:
                    sum_age += int(employee.birth_years)
                    contract = self.env['hr.contract'].search([('employee_id', '=', employee.id)], limit=1)
                    sum_salary += int(contract.wage)
                    list_salary.append(int(contract.wage))
                if len(employees):
                    avg_age = sum_age / len(employees)
                    avg_salary = sum_salary / len(employees)
                if list_salary:
                    lowest_salary = min(list_salary)
                    highest_salary = max(list_salary)
                    if len(list_salary) < 2:
                        standard_deviation = 0
                    else:
                        standard_deviation = stdev(list_salary)

                low_average_salary = avg_salary - standard_deviation
                high_average_salary = avg_salary + standard_deviation
                if employees:
                    retention_rate = ((len(employees) - employees_out) / float(len(employees))) * 100
                else:
                    retention_rate = 0

                datas.append({
                    'department': dept.name,
                    'job_position': position.name,
                    'current_employee': (len(employees)),
                    'male': male_employees,
                    'female': female_employees,
                    'other': other_employees,
                    'avg_age': avg_age,
                    'total_in': employees_in,
                    'total_out': employees_out,
                    'retention_rate': retention_rate,
                    'avg_salary': avg_salary,
                    'lowest_salary': lowest_salary,
                    'highest_salary': highest_salary,
                    'standard_deviation': standard_deviation,
                    'low_average_salary': low_average_salary,
                    'high_average_salary': high_average_salary
                })
        if datas:
            file_name = 'Employee Report ' + str(start) + ' - ' + str(end) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format0 = xlwt.easyxf('font:height 230,bold True; align: horiz left')
            format1 = xlwt.easyxf('font:height 230,bold True; align: horiz center')
            format2 = xlwt.easyxf('font:height 230; align: horiz left')
            format3 = xlwt.easyxf('font:height 230; align: horiz center')
            sheet = workbook.add_sheet('Employee Report')
            sheet.col(0).width = int(25 * 250)
            sheet.col(1).width = int(25 * 250)
            sheet.col(2).width = int(25 * 300)
            sheet.col(6).width = int(25 * 250)
            sheet.col(9).width = int(25 * 250)
            sheet.col(10).width = int(25 * 250)
            sheet.col(11).width = int(25 * 250)
            sheet.col(12).width = int(25 * 250)
            sheet.col(13).width = int(25 * 250)
            sheet.col(14).width = int(25 * 250)
            sheet.col(15).width = int(25 * 250)
            sheet.write(1, 3, "Report Employee Analysis", format0)
            sheet.write(3, 0, "Periode", format0)
            sheet.write(3, 1, str(start) + ' - ' + str(end), format3)
            sheet.write(4, 0, "Company", format0)
            sheet.write(4, 1, company, format3)
            sheet.write(5, 0, "Department", format0)
            sheet.write(5, 1, ", ".join(department_list), format2)

            sheet.write(7, 0, 'Department', format1)
            sheet.write(7, 1, 'Job Position', format1)
            sheet.write(7, 2, 'Current Number of Employees', format1)
            sheet.write(7, 3, 'Male', format1)
            sheet.write(7, 4, 'Female', format1)
            sheet.write(7, 5, 'Others', format1)
            sheet.write(7, 6, 'Average Age', format1)
            sheet.write(7, 7, 'Total In', format1)
            sheet.write(7, 8, 'Total Out', format1)
            sheet.write(7, 9, 'Retention Rate (%)', format1)
            sheet.write(7, 10, 'Average Salary', format1)
            sheet.write(7, 11, 'Lowest Salary', format1)
            sheet.write(7, 12, 'Highest Salary', format1)
            sheet.write(7, 13, 'Standard Deviation', format1)
            sheet.write(7, 14, 'Low Average Salary', format1)
            sheet.write(7, 15, 'High Average Salary', format1)

            row = 9
            for line in datas:
                sheet.write(row, 0, line.get('department'), format3)
                sheet.write(row, 1, line.get('job_position'), format2)
                sheet.write(row, 2, line.get('current_employee'), format3)
                sheet.write(row, 3, line.get('male'), format3)
                sheet.write(row, 4, line.get('female'), format3)
                sheet.write(row, 5, line.get('other'), format3)
                sheet.write(row, 6, line.get('avg_age'), format3)
                sheet.write(row, 7, line.get('total_in'), format3)
                sheet.write(row, 8, line.get('total_out'), format3)
                sheet.write(row, 9, line.get('retention_rate'), format3)
                sheet.write(row, 10, line.get('avg_salary'), format3)
                sheet.write(row, 11, line.get('lowest_salary'), format3)
                sheet.write(row, 12, line.get('highest_salary'), format3)
                sheet.write(row, 13, line.get('standard_deviation'), format3)
                sheet.write(row, 14, line.get('low_average_salary'), format3)
                sheet.write(row, 15, line.get('high_average_salary'), format3)
                row += 1

            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.employee.reporting.attachment'].create(
                {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Employee Report',
                'res_model': 'hr.employee.reporting.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))

class HrEmployeeReportingAttachment(models.TransientModel):
    _name = "hr.employee.reporting.attachment"
    _description = "Employee Report Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')