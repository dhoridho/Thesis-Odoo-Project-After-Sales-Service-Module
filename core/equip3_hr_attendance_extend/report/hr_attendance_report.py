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

class HrAttendanceReportExcel(models.TransientModel):
    _name = "hr.attendance.report.excel"
    _description = "HR Attendance Report Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')

class HrAttendanceReport(models.TransientModel):
    _name = 'hr.attendance.report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    work_location_ids = fields.Many2many('work.location.object', string='Work Location', required=True)
    specify_by = fields.Selection([('department', 'Department'),('job_position', 'Job Position'),
                                   ('employee', 'Employee'),('tag', 'Tag')], string='Specify By', required=True)
    all_department = fields.Boolean(string="All Department")
    department_ids = fields.Many2many('hr.department', string='Department')
    all_job_position = fields.Boolean(string="All Job Position")
    job_position_ids = fields.Many2many('hr.job', string='Job Position')
    all_employee = fields.Boolean(string="All Employee")
    employee_ids = fields.Many2many('hr.employee', string='Employee')
    all_tag = fields.Boolean(string="All Tag")
    tag_ids = fields.Many2many('hr.employee.category', string='Tag')

    @api.onchange('specify_by')
    def onchange_specify_by(self):
        for rec in self:
            if rec.specify_by:
                rec.all_department = False
                rec.all_job_position = False
                rec.all_employee = False
                rec.all_tag = False
                rec.department_ids = [(5,0,0)]
                rec.job_position_ids = [(5,0,0)]
                rec.employee_ids = [(5,0,0)]
                rec.tag_ids = [(5,0,0)]
    
    @api.onchange('all_department')
    def onchange_all_department(self):
        for rec in self:
            if rec.all_department:
                dept_obj = self.env[('hr.department')].search([('active','=',True)])
                dept_ids = []
                for dept in dept_obj:
                    dept_ids.append(dept.id)
                rec.department_ids = dept_ids
            else:
                rec.department_ids = [(5,0,0)]
    
    @api.onchange('all_job_position')
    def onchange_all_job_position(self):
        for rec in self:
            if rec.all_job_position:
                job_obj = self.env[('hr.job')].search([])
                job_ids = []
                for job in job_obj:
                    job_ids.append(job.id)
                rec.job_position_ids = job_ids
            else:
                rec.job_position_ids = [(5,0,0)]
    
    @api.onchange('all_employee')
    def onchange_all_employee(self):
        for rec in self:
            if rec.all_employee:
                emp_obj = self.env[('hr.employee')].search([('active','=',True)])
                emp_ids = []
                for emp in emp_obj:
                    emp_ids.append(emp.id)
                rec.employee_ids = emp_ids
            else:
                rec.employee_ids = [(5,0,0)]
    
    @api.onchange('all_tag')
    def onchange_all_tag(self):
        for rec in self:
            if rec.all_tag:
                tag_obj = self.env[('hr.employee.category')].search([])
                tag_ids = []
                for tag in tag_obj:
                    tag_ids.append(tag.id)
                rec.tag_ids = tag_ids
            else:
                rec.tag_ids = [(5,0,0)]

    @api.constrains('start_date','end_date')
    def _check_start_end_date(self):
        if self.start_date > self.end_date:
            raise ValidationError("End Date must grather than Start Date")
    
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

        domain = [('start_working_date', '>=', self.start_date), ('start_working_date', '<=', self.end_date)]
            
        domain_employee = [('active','=',True)]
        if self.work_location_ids:
            domain_employee.append(('location_id', 'in', self.work_location_ids.ids))
        
        if self.specify_by == "department":
            domain_employee.append(('department_id', 'in', self.department_ids.ids))
        elif self.specify_by == "job_position":
            domain_employee.append(('job_id', 'in', self.job_position_ids.ids))
        elif self.specify_by == "employee":
            domain_employee.append(('id', 'in', self.employee_ids.ids))
        elif self.specify_by == "tag":
            domain_employee.append(('category_ids', 'in', self.tag_ids.ids))

        employee_data = self.env['hr.employee'].search(domain_employee,order="sequence_code asc")
        if not employee_data:
            raise ValidationError(_('There is no Employee Data on specific selection.'))
        domain.append(('employee_id', 'in', employee_data.ids))
        attendance_obj = self.env['hr.attendance'].search(domain,order="start_working_date asc")

        attendance_data = []
        for emp in employee_data:
            num_work_days = 0
            worked_days = 0
            paid_leaves = 0
            unpaid_days = 0

            working_cal_list = []
            working_calendar_obj = self.env['employee.working.schedule.calendar'].search([('employee_id','=',emp.id),('date_start', '>=', self.start_date), ('date_start', '<=', self.end_date)])
            for cal in working_calendar_obj:
                if cal.date_start not in working_cal_list:
                    working_cal_list.append(cal.date_start)
            num_work_days += len(working_cal_list)

            for att in attendance_obj:
                if att.employee_id.id == emp.id:
                    if att.attendance_status == "present":
                        worked_days += 1
                    elif att.attendance_status == "leave":
                        paid_leaves += 1
                    elif att.attendance_status == "absent":
                        unpaid_days += 1
            paid_leaves_worked_days = paid_leaves + worked_days
            if num_work_days > 0:
                attendance_ratio = (worked_days / num_work_days) * 100
            else:
                attendance_ratio = 0
            #Leave type Start
            leave_type = self.env['hr.leave.type'].search([('is_show_attendance_report', '=', True)])
            # Leave type End

            employee_tag = []
            for tag in emp.category_ids:
                employee_tag += [tag.name]
            employee_tag = ', '.join(employee_tag)

            attendance_data.append({
                'sequence_code': emp.sequence_code,
                'employee_name': emp.name,
                'emp_id': emp.id,
                'department': emp.department_id.name,
                'employee_tag': employee_tag,
                'job_position': emp.job_id.name,
                'work_location': emp.location_id.name,
                'num_work_days': num_work_days,
                'worked_days': worked_days,
                'paid_leaves': paid_leaves,
                'paid_leaves_worked_days': paid_leaves_worked_days,
                'unpaid_days': unpaid_days,
                'attendance_ratio': attendance_ratio
            })
        
        if attendance_data:
            file_name = 'Attendance Report ' + period + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            left_bold = xlwt.easyxf('font:height 200,bold True; align: horiz left;')
            left = xlwt.easyxf('font:height 200; align: horiz left;')
            center_bold = xlwt.easyxf('font:height 200, bold True; align: horiz center;')
            center = xlwt.easyxf('font:height 200; align: horiz center;')
            right = xlwt.easyxf('font:height 200; align: horiz right;')
            sheet = workbook.add_sheet('Attendance Report')
            sheet.col(0).width = int(25 * 200)
            sheet.col(1).width = int(25 * 300)
            sheet.col(2).width = int(25 * 300)
            sheet.col(3).width = int(25 * 300)
            sheet.col(4).width = int(25 * 300)
            sheet.col(5).width = int(25 * 300)
            sheet.col(6).width = int(25 * 200)
            sheet.col(7).width = int(25 * 200)
            sheet.col(8).width = int(25 * 200)
            sheet.col(9).width = int(25 * 300)
            sheet.col(10).width = int(25 * 300)
            sheet.col(11).width = int(25 * 300)
            sheet.col(12).width = int(25 * 200)
            sheet.col(13).width = int(25 * 300)

            sheet.write(0, 0, "Attendance Report - Period " + period, left_bold)
            sheet.write(2, 0, "Employee ID", center_bold)
            sheet.write(2, 1, "Employee Name", center_bold)
            sheet.write(2, 2, "Department", center_bold)
            sheet.write(2, 3, "Tag", center_bold)

            sheet.write(2, 4, "Job Position", center_bold)
            sheet.write(2, 5, "Work Location", center_bold)
            sheet.write(2, 6, "Number of Work Days", center_bold)
            sheet.write(2, 7, "Worked Days", center_bold)
            # Leave Type Dynamic Heading Start
            col = 8
            for heading in leave_type:
                sheet.write(2, col, heading.name, center_bold)
                col += 1
            # Leave Type Dynamic Heading End
            sheet.write(2, col, "Paid Leaves", center_bold)
            sheet.write(2, col+1, "Paid Leaves + Worked Days", center_bold)
            sheet.write(2, col+2, "Unpaid Days", center_bold)
            sheet.write(2, col+3, "Attendance Ratio (%)", center_bold)
            
            row = 3
            for cal in attendance_data:
                sheet.write(row, 0, cal.get('sequence_code'), center)
                sheet.write(row, 1, cal.get('employee_name'), left)
                sheet.write(row, 2, cal.get('department'), left)
                sheet.write(row, 3, cal.get('employee_tag'), left)
                sheet.write(row, 4, cal.get('job_position'), left)
                sheet.write(row, 5, cal.get('work_location'), left)
                sheet.write(row, 6, cal.get('num_work_days'), right)
                sheet.write(row, 7, cal.get('worked_days'), right)
                # Leave calculation Start
                col = 8
                emp_id = cal.get('emp_id')
                for l_type in leave_type:
                    employee_leave = self.env['hr.leave'].search([
                        ('state', 'in', ['confirm', 'validate', 'validate1']),
                        ('holiday_status_id', '=', l_type.id),
                        ('employee_id', '=', int(emp_id)),
                        ('request_date_from', '<=', self.end_date), ('request_date_to', '>=', self.start_date),
                    ])
                    total_leave_days = 0.0
                    for emp_leave in employee_leave:
                        if emp_leave.holiday_status_id.id == l_type.id:
                            total_leave_days += emp_leave.number_of_days
                    num_leave_days = total_leave_days
                    sheet.write(row, col, num_leave_days, right)
                    col += 1
                # Leave calculation End
                sheet.write(row, col, cal.get('paid_leaves'), right)
                sheet.write(row, col+1, cal.get('paid_leaves_worked_days'), right)
                sheet.write(row, col+2, cal.get('unpaid_days'), right)
                sheet.write(row, col+3, "{:0,.2f}".format(cal.get('attendance_ratio')), right)
                row += 1
            
            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.attendance.report.excel'].create(
                {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Attendance Report',
                'res_model': 'hr.attendance.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))