# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import time
import pytz
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HrDailyAttendanceReportAttachment(models.TransientModel):
    _name = "hr.daily.attendance.report.attachment"
    _description = "HR Daily Attendance Report Attachment"

    attachment_file = fields.Binary('Attachment Report')
    attachment_name = fields.Char('Attachment Name')

class HrDailyAttendanceReport(models.TransientModel):
    _name = 'hr.daily.attendance.report'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    all_attendance_status = fields.Boolean(string="All Attendance Status")
    attendance_status = fields.Selection([('present', 'Present'),('absent', 'Absent'),
                                          ('leave', 'Leave'),('travel', 'Travel')],
                                          string='Attendance Status')
    specify_by = fields.Selection([('department', 'Department'),('job_position', 'Job Position'),
                                   ('employee', 'Employee')], string='Specify By', required=True)
    all_department = fields.Boolean(string="All Department")
    department_ids = fields.Many2many('hr.department', string='Department')
    all_job_position = fields.Boolean(string="All Job Position")
    job_position_ids = fields.Many2many('hr.job', string='Job Position')
    all_employee = fields.Boolean(string="All Employee")
    employee_ids = fields.Many2many('hr.employee', string='Employee')
    file_type = fields.Selection([('pdf', 'pdf'),('xlsx', 'xlsx')], string='File Type', required=True)

    @api.onchange('all_attendance_status')
    def onchange_all_attendance_status(self):
        for rec in self:
            if rec.all_attendance_status:
                rec.attendance_status = ""

    @api.onchange('specify_by')
    def onchange_specify_by(self):
        for rec in self:
            if rec.specify_by:
                rec.all_department = False
                rec.all_job_position = False
                rec.all_employee = False
                rec.department_ids = [(5,0,0)]
                rec.job_position_ids = [(5,0,0)]
                rec.employee_ids = [(5,0,0)]
    
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
    
    @api.constrains('start_date','end_date')
    def _check_start_end_date(self):
        if self.start_date > self.end_date:
            raise ValidationError("End Date must grather than Start Date")

    def convert_float_time(self, data):
        if data >= 0:
            return '{0:02.0f}:{1:02.0f}'.format(*divmod(float(data) * 60, 60))
        else:
            return '-{0:02.0f}:{1:02.0f}'.format(*divmod(float(data) * -60, 60))
    
    def action_print(self):
        period = str(self.start_date.strftime("%d"))+'/'+str(self.start_date.strftime("%m"))+'/'+str(self.start_date.strftime("%Y"))+' to '+str(self.end_date.strftime("%d"))+'/'+str(self.end_date.strftime("%m"))+'/'+str(self.end_date.strftime("%Y"))
        if self.all_attendance_status:
            domain = [('start_working_date','>=',self.start_date),('start_working_date','<=',self.end_date)]
        else:
            domain = [('start_working_date','>=',self.start_date),('start_working_date','<=',self.end_date),('attendance_status','=',self.attendance_status)]
        domain_employee = [('active','=',True)]
        if self.specify_by == "department":
            domain_employee.append(('department_id', 'in', self.department_ids.ids))
        elif self.specify_by == "job_position":
            domain_employee.append(('job_id', 'in', self.job_position_ids.ids))
        elif self.specify_by == "employee":
            domain_employee.append(('id', 'in', self.employee_ids.ids))

        employee_data = self.env['hr.employee'].search(domain_employee,order="sequence_code asc")
        if not employee_data:
            raise ValidationError(_('There is no Employee Data on specific selection.'))
        domain.append(('employee_id', 'in', employee_data.ids))
        attendance_obj = self.env['hr.attendance'].search(domain,order="start_working_date asc")
        
        attendance_data = []
        for att in attendance_obj:
            employee_tz = att.employee_id.tz or 'UTC'
            local = pytz.timezone(employee_tz)
            
            checkin_time = ""
            checkout_time = ""
            if att.check_in:
                check_in = pytz.UTC.localize(att.check_in).astimezone(local)
                checkin_time_val = check_in.time()
                checkin_float = checkin_time_val.hour + checkin_time_val.minute / 60
                checkin_time = self.convert_float_time(checkin_float)
            if att.check_out:
                checkout = pytz.UTC.localize(att.check_out).astimezone(local)
                checkout_time_val = checkout.time()
                checkout_float = checkout_time_val.hour + checkout_time_val.minute / 60
                checkout_time = self.convert_float_time(checkout_float)

            overtime = 0
            coefficient_hours = 0
            meal_allowance = 0
            overtime_line = self.env['hr.overtime.actual.line'].sudo().search([('date','=',att.start_working_date),('employee_id','=',att.employee_id.id),('state','=','approved')])
            if overtime_line:
                for ovt in overtime_line:
                    overtime += ovt.actual_hours
                    coefficient_hours += ovt.coefficient_hours
                    meal_allowance += ovt.meal_allowance

            attendance_data.append({
                'date': att.start_working_date,
                'employee': att.employee_id.name,
                'employee_id': att.employee_id.sequence_code if att.employee_id.sequence_code else "",
                'job_position': att.employee_id.job_id.name if att.employee_id.job_id else "",
                'department': att.employee_id.department_id.name if att.employee_id.department_id else "",
                'working_schedule': att.working_schedule_id.name if att.working_schedule_id else "",
                'work_from': self.convert_float_time(att.hour_from),
                'work_to': self.convert_float_time(att.hour_to),
                'check_in': checkin_time,
                'checkin_status': "No Checkin" if att.checkin_status == "no_checking" else att.checkin_status.title().replace("_"," "),
                'check_in_diff': self.convert_float_time(att.check_in_diff),
                'check_out': checkout_time,
                'checkout_status': att.checkout_status.title().replace("_"," "),
                'check_out_diff': self.convert_float_time(att.check_out_diff),
                'break_from': self.convert_float_time(att.calendar_id.break_from) if att.calendar_id else "",
                'break_to': self.convert_float_time(att.calendar_id.break_to) if att.calendar_id else "",
                'worked_hours': self.convert_float_time(att.worked_hours),
                'overtime': self.convert_float_time(overtime),
                'coefficient_hours': coefficient_hours,
                'meal_allowance': meal_allowance,
                'attendance_status': att.attendance_status.title(),
            })
            
        if self.file_type == 'xlsx':
            if attendance_data:
                file_name = 'Daily Attendance Report ' + period + '.xls'
                workbook = xlwt.Workbook(encoding="UTF-8")
                center_bold = xlwt.easyxf('font:height 300, bold True; align: horiz center;')
                center = xlwt.easyxf('font:height 200; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
                left = xlwt.easyxf('font:height 200; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
                right = xlwt.easyxf('font:height 200; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
                formatdate = xlwt.easyxf('font:height 210; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;', num_format_str='dd/MM/yyyy')
                sheet = workbook.add_sheet('Daily Attendance Report')

                for i in range(0, 21):
                    sheet.col(i).width = int(25 * 210)
                
                if self.all_attendance_status:
                    text_att_status = "All"
                else:
                    text_att_status = self.attendance_status.title()

                sheet.write_merge(0, 0, 0, 20, "Daily Attendance Report", center_bold)
                sheet.write_merge(1, 1, 0, 20, "Period: " + period, center_bold)
                sheet.write_merge(2, 2, 0, 20, "Attendance Status: " + text_att_status, center_bold)
                sheet.write_merge(4, 5, 0, 0, "Date", center)
                sheet.write_merge(4, 5, 1, 1, "Employee", center)
                sheet.write_merge(4, 5, 2, 2, "Employee ID", center)
                sheet.write_merge(4, 5, 3, 3, "Job Position", center)
                sheet.write_merge(4, 5, 4, 4, "Department", center)
                sheet.write_merge(4, 5, 5, 5, "Working Schedule", center)
                sheet.write_merge(4, 5, 6, 6, "Work From", center)
                sheet.write_merge(4, 5, 7, 7, "Work To", center)
                sheet.write_merge(4, 4, 8, 13, "Actual Attendance", center)
                sheet.write(5, 8, "Check In", center)
                sheet.write(5, 9, "Check In Status", center)
                sheet.write(5, 10, "Check In Difference", center)
                sheet.write(5, 11, "Check Out", center)
                sheet.write(5, 12, "Check Out Status", center)
                sheet.write(5, 13, "Check Out Difference", center)
                sheet.write_merge(4, 5, 14, 14, "Break From", center)
                sheet.write_merge(4, 5, 15, 15, "Break To", center)
                sheet.write_merge(4, 5, 16, 16, "Worked Hours", center)
                sheet.write_merge(4, 5, 17, 17, "Overtime", center)
                sheet.write_merge(4, 5, 18, 18, "Coefficient Hours", center)
                sheet.write_merge(4, 5, 19, 19, "Meal Allowance", center)
                sheet.write_merge(4, 5, 20, 20, "Attendance Status", center)

                row = 6
                for cal in attendance_data:
                    sheet.write(row, 0, cal.get('date'), formatdate)
                    sheet.write(row, 1, cal.get('employee'), left)
                    sheet.write(row, 2, cal.get('employee_id'), center)
                    sheet.write(row, 3, cal.get('job_position'), left)
                    sheet.write(row, 4, cal.get('department'), left)
                    sheet.write(row, 5, cal.get('working_schedule'), left)
                    sheet.write(row, 6, cal.get('work_from'), right)
                    sheet.write(row, 7, cal.get('work_to'), right)
                    sheet.write(row, 8, cal.get('check_in'), right)
                    sheet.write(row, 9, cal.get('checkin_status'), left)
                    sheet.write(row, 10, cal.get('check_in_diff'), right)
                    sheet.write(row, 11, cal.get('check_out'), right)
                    sheet.write(row, 12, cal.get('checkout_status'), left)
                    sheet.write(row, 13, cal.get('check_out_diff'), right)
                    sheet.write(row, 14, cal.get('break_from'), right)
                    sheet.write(row, 15, cal.get('break_to'), right)
                    sheet.write(row, 16, cal.get('worked_hours'), right)
                    sheet.write(row, 17, cal.get('overtime'), right)
                    sheet.write(row, 18, cal.get('coefficient_hours'), right)
                    sheet.write(row, 19, cal.get('meal_allowance'), right)
                    sheet.write(row, 20, cal.get('attendance_status'), left)
                    row += 1

                fp = BytesIO()
                workbook.save(fp)
                export_id = self.env['hr.daily.attendance.report.attachment'].create(
                    {'attachment_file': base64.encodebytes(fp.getvalue()), 'attachment_name': file_name})
                fp.close()
                return {
                    'view_mode': 'form',
                    'res_id': export_id.id,
                    'name': 'Daily Attendance Report',
                    'res_model': 'hr.daily.attendance.report.attachment',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                raise ValidationError(_('There is no Data.'))
        elif self.file_type == 'pdf':
            if attendance_data:
                file_name = 'Daily Attendance Report ' + period + '.pdf'

                if self.all_attendance_status:
                    text_att_status = "All"
                else:
                    text_att_status = self.attendance_status.title()

                datas = {
                    'period': period,
                    'text_att_status': text_att_status,
                    'attendance_data': attendance_data,
                }
                pdf = self.env.ref('equip3_hr_attendance_extend.action_hr_daily_attendance_report')._render_qweb_pdf([], data=datas)
                attachment = base64.b64encode(pdf[0])
                export_id = self.env['hr.daily.attendance.report.attachment'].create(
                        {'attachment_file': attachment, 'attachment_name': file_name})
                return {
                        'view_mode': 'form',
                        'res_id': export_id.id,
                        'name': 'Daily Attendance Report',
                        'res_model': 'hr.daily.attendance.report.attachment',
                        'view_type': 'form',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                    }
            else:
                raise ValidationError(_('There is no Data.'))