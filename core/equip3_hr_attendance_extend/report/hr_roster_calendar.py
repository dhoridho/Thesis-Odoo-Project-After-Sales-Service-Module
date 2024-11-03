# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HrRosterCalendarExcel(models.TransientModel):
    _name = "hr.roster.calendar.excel"
    _description = "Roster Calendar Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')

class HrRosterCalendar(models.TransientModel):
    _name = 'hr.roster.calendar'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    work_location_ids = fields.Many2many('work.location.object', string='Work Location', required=True, domain=_multi_company_domain)
    all_department = fields.Boolean(string="All Department")
    department_ids = fields.Many2many('hr.department', string='Department', domain=_multi_company_domain)

    @api.constrains('start_date','end_date')
    def _check_start_end_date(self):
        if self.start_date > self.end_date:
            raise ValidationError("End Date must grather than Start Date")

    def convert_float_time(self, data):
        return '{0:02.0f}:{1:02.0f}'.format(*divmod(float(data) * 60, 60))

    def action_print_xls(self):
        col_dates = []
        col_no = 2
        start_date = self.start_date
        end_date = self.end_date
        while start_date <= end_date:
            row = [None, None]
            row[0] = col_no
            row[1] = start_date
            col_dates.append(row)
            col_no += 1
            start_date += relativedelta(days=1)

        period = str(self.start_date.strftime("%d"))+'/'+str(self.start_date.strftime("%m"))+'/'+str(self.start_date.strftime("%Y"))+' to '+str(self.end_date.strftime("%d"))+'/'+str(self.end_date.strftime("%m"))+'/'+str(self.end_date.strftime("%Y"))

        work_location = []
        for location in self.work_location_ids:
            work_location += [location.name]
        work_location = ', '.join(work_location)

        department = []
        if self.all_department:
            department = "All"
        else:
            for dept in self.department_ids:
                department += [dept.name]
            department = ', '.join(department)

        domain = [('date_start', '>=', self.start_date), ('date_start', '<=', self.end_date)]
        if self.work_location_ids:
            employee_ids = self.env['hr.employee'].search([('location_id', 'in', self.work_location_ids.ids)])
            domain.append(('employee_id', 'in', employee_ids.ids))
        if not self.all_department:
            domain.append(('department_id', 'in', self.department_ids.ids))
            employee_data = self.env['hr.employee'].search([('location_id', 'in', self.work_location_ids.ids),('department_id', 'in', self.department_ids.ids)],order="department_id asc")
        else:
            employee_data = self.env['hr.employee'].search([('location_id', 'in', self.work_location_ids.ids)],order="department_id asc")
            
        working_calendar = self.env['employee.working.schedule.calendar'].search(domain,order="date_start asc")

        temp_list = []
        calendar_data = []
        if employee_data:
            for employee in employee_data:
                for cal in working_calendar:
                    if cal.employee_id.id == employee.id:
                        row = [None, None]
                        row[0] = cal.date_start
                        row[1] = '(' + self.convert_float_time(cal.hour_from) + '-' + self.convert_float_time(cal.hour_to) + ')'
                        if {'location': employee.location_id.id,'department': employee.department_id.id,'employee': employee.id} in temp_list:
                            filter_list = list(filter(lambda r: r.get('location').id == employee.location_id.id and r.get('department').id == employee.department_id.id and r.get('employee').id == employee.id,  calendar_data))
                            if filter_list:
                                index_no = 0
                                date_list = []
                                for rows in filter_list[0]['date_start']:
                                    date_list += [rows[0]]

                                if row[0] not in date_list:
                                    filter_list[0]['date_start'].append(row)
                                else:
                                    index_no = 0
                                    for rows in filter_list[0]['date_start']:
                                        if rows[0] == row[0]:
                                            filter_list[0]['date_start'][index_no][1] += ' (' + self.convert_float_time(cal.hour_from) + '-' + self.convert_float_time(cal.hour_to) + ')'
                                        index_no += 1
                        else:
                            temp_list.append({'location': employee.location_id.id,'department': employee.department_id.id,'employee': employee.id})
                            calendar_data.append({
                                'location': employee.location_id,
                                'department': employee.department_id,
                                'employee': employee,
                                'date_start': [row]
                            })

        file_name = 'Roster Calendar ' + period + '.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        left_bold = xlwt.easyxf('font:height 200,bold True; align: horiz left;')
        left = xlwt.easyxf('font:height 200; align: horiz left;')
        center_bold = xlwt.easyxf('font:height 200, bold True; align: horiz center;')
        date_center_bold = xlwt.easyxf('font:height 200, bold True; align: horiz center;', num_format_str='DD/MM/YYYY')
        center = xlwt.easyxf('font:height 200; align: horiz center;')
        right = xlwt.easyxf('font:height 200; align: horiz right;')
        sheet = workbook.add_sheet('Roster Calendar')
        sheet.col(0).width = int(25 * 200)
        sheet.col(1).width = int(25 * 200)
        for work_date in col_dates:
            sheet.col(work_date[0]).width = int(25 * 300)
        sheet.write(0, 2, "Roster Calendar", left_bold)
        sheet.write(2, 0, "Working Date", left_bold)
        sheet.write(2, 1, period, left)
        sheet.write(3, 0, "Work Location", left_bold)
        sheet.write(3, 1, str(work_location), left)
        sheet.write(4, 0, "Department", left_bold)
        sheet.write(4, 1, department, left)
        sheet.write_merge(7, 8, 0, 0, 'Work Location', center_bold)
        sheet.write_merge(7, 8, 1, 1, 'Department', center_bold)
        sheet.write_merge(7, 7, 2, col_no, 'Working Date', center_bold)
        for work_date in col_dates:
            sheet.write(8, work_date[0], work_date[1], date_center_bold)

        row_x = 9
        row_y = 9
        for cal in calendar_data:
            sheet.write(row_x, 0, cal.get('location').name, center)
            sheet.write(row_x, 1, cal.get('department').name, center)
            for work_date in col_dates:
                employee_data = ""
                for time in cal.get('date_start'):
                    if time[0] == work_date[1]:
                        employee_data = cal.get('employee').name + ' ' + time[1]
                sheet.write(row_y, work_date[0], employee_data, left)

            row_x += 1
            row_y += 1

        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['hr.roster.calendar.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'name': 'Roster Calendar',
            'res_model': 'hr.roster.calendar.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }