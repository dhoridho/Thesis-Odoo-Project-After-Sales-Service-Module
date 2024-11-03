# Copyright (C) Softhealer Technologies.

from odoo import http
from odoo.http import request
from datetime import timedelta,datetime
from dateutil.relativedelta import relativedelta



class HRDashboard(http.Controller):

    @http.route('/get_employee_expense_data', type='http', auth="public", methods=['GET'])
    def get_employee_expense_data(self, **post):
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee:
            expenses = request.env['hr.expense'].sudo().search(
                [('employee_id.user_id', '=', request.env.user.id)], limit=10)
        elif group_manager:
            expenses = request.env['hr.expense'].sudo().search(
                [], limit=10)
        else:
            expenses = request.env['hr.expense'].sudo().search(
                [], limit=10)
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_expense_data_tbl', {'expenses': expenses})

    def previous_week_range(self,date):
        start_date = date + timedelta(-date.weekday(), weeks=-1)
        end_date = date + timedelta(-date.weekday() - 1)
        return start_date, end_date
    
    def now_week_range(self,date):
        start_date = date - timedelta(days=date.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date

    @http.route('/get_employee_attendance_data', type='http', auth="public", methods=['GET'])
    def get_employee_attendance_data(self, **post):
        now = datetime.now()
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee:
            attendances = request.env['hr.attendance'].sudo().search(
                [('employee_id.user_id', '=', request.env.user.id)], limit=10)
        elif group_manager:
            last_week_start,last_week_end = self.previous_week_range(now.date())
            employee_ids = []
            attendance_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id','=',request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            attendances_list = request.env['hr.attendance'].sudo().search(
                [('employee_id','in',employee_ids)], limit=50,order='start_working_date desc')
            attendance_ids.extend(data_attendance.id for data_attendance in attendances_list if data_attendance.start_working_date >= last_week_start and data_attendance.start_working_date <= now.date() )
            attendances = request.env['hr.attendance'].sudo().browse(attendance_ids)
        else:
            attendances = request.env['hr.attendance'].sudo().search(
                [], limit=10)
        attendance_dic = {}
        for attendance in attendances:
            data_list = []
            if attendance.check_in:
                data_list.append(attendance.check_in + timedelta(minutes=330))
            else:
                data_list.append('')

            if attendance.check_out:
                data_list.append(attendance.check_out + timedelta(minutes=330))
            else:
                data_list.append('')

            attendance_dic[attendance] = data_list
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_attendance_data_tbl', {'attendance_dic': attendance_dic})

    @http.route('/get_employee_leave_data', type='http', auth="public", methods=['GET'])
    def get_employee_leave_data(self, **post):
        now = datetime.now()
        start_date,end_date = self.now_week_range(now.date())
        next_start_date,next_end_date = self.now_week_range(now.date()+timedelta(days=7))
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee:
            leaves = request.env['hr.leave'].sudo().search(
                [('employee_id.user_id', '=', request.env.user.id)], limit=10)
        elif group_manager:
            employee_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id','=',request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            leaves = request.env['hr.leave'].sudo().search(
                [('employee_id','in',employee_ids),('request_date_from','>=',start_date),('request_date_from','<=',next_end_date)], limit=10,order='request_date_from desc')
        else:
            leaves = request.env['hr.leave'].sudo().search(
                [], limit=10)
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_leave_data_tbl', {'leaves': leaves})

    @http.route('/get_annoucement_data', type='http', auth="public", methods=['GET'])
    def get_annoucement_data(self, **post):
        annoucements = request.env['sh.annoucement'].sudo().search(
            [], order='sequence', limit=10)
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_annoucements_data_tbl', {'annoucements': annoucements})

    @http.route('/get_employee_birhday_data', type='http', auth="public", methods=['GET'])
    def get_employee_birhday_data(self, **post):
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee and group_manager:
            employees = request.env['hr.employee'].sudo().search([])
        elif group_employee:
            employees = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
        elif group_manager:
            employee_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id','=',request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            employees = request.env['hr.employee'].sudo().search([('id','in',employee_ids)])
        else:
            employees = request.env['hr.employee'].sudo().search([])
        employee_birthday_dic = {}
        today = datetime.today()
        todays_date = today.strftime("%m-%d")
        for employee in employees:
            if employee.birthday:
                birthdate = datetime.strptime(
                    employee.birthday.strftime("%m-%d"), "%m-%d")
                current_date = datetime.strptime(todays_date, "%m-%d")
                ## start add by hadorik
                this_month = today.month
                birthdate_month = datetime.strptime(str(employee.birthday), '%Y-%m-%d').date().month

                if (this_month == birthdate_month):
                ## end add
                    if(current_date >= birthdate):
                        days_diff = (current_date - birthdate).days
                        past_days = (current_date - birthdate).days

                        current_year = today.strftime("%Y")
                        if days_diff == 0:
                            employee_birthday_dic[employee] = days_diff
                        else:
                            if int(current_year) % 4 == 0:
                                days_diff = 366 - days_diff
                            else:
                                days_diff = 365 - days_diff
                    else:
                        days_diff = (birthdate-current_date).days
                        past_days = 0

                    # if days_diff >= 0:
                    #     employee_birthday_dic[employee] = days_diff

                    if days_diff >= 0:
                        employee_birthday_dic[employee] = [days_diff]

                    if past_days >= 0:
                        if employee in employee_birthday_dic:
                            employee_birthday_dic[employee].append(past_days)
                        else:
                            employee_birthday_dic[employee] = [past_days]

        sort_employee_birthday_dic = sorted(
            employee_birthday_dic.items(), key=lambda x: x[1][1])
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_birthday_data_tbl', {'sort_employee_birthday_dic': sort_employee_birthday_dic})

    @http.route('/get_employee_anniversary_data', type='http', auth="public", methods=['GET'])
    def get_employee_anniversary_data(self, **post):
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee and group_manager:
            employees = request.env['hr.employee'].sudo().search([])
        elif group_employee:
            employees = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
        elif group_manager:
            employee_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id','=',request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            employees = request.env['hr.employee'].sudo().search([('id','in',employee_ids)])
        else:
            employees = request.env['hr.employee'].sudo().search([])
        employee_anni_dic = {}
        today = datetime.today()
        todays_date = today.strftime("%m-%d")
        for employee in employees:
            if employee.date_of_joining:
                current_date = datetime.strptime(todays_date, "%m-%d")
                anni_date = datetime.strptime(
                    employee.date_of_joining.strftime("%m-%d"), "%m-%d")

                current_year = today.strftime("%Y")
                this_month = today.month
                anni_date_month = datetime.strptime(str(employee.date_of_joining), '%Y-%m-%d').date().month
                delta = relativedelta(today, employee.date_of_joining)

                if (this_month == anni_date_month) and delta.years >= 1:
                    if(current_date >= anni_date):
                        days_diff = (current_date - anni_date).days

                        current_year = today.strftime("%Y")
                        if days_diff == 0:
                            employee_anni_dic[employee] = days_diff
                        else:
                            if int(current_year) % 4 == 0:
                                days_diff = 366 - days_diff
                            else:
                                days_diff = 365 - days_diff

                        employee_anni_dic[employee] = days_diff
                    else:
                        days_diff = (anni_date-current_date).days

                        employee_anni_dic[employee] = days_diff

        sort_employee_anni_dic = sorted(
            employee_anni_dic.items(), key=lambda x: x[1])
        employee_anni_dic = {}
        for data in sort_employee_anni_dic:
            employee = data[0]
            anniversary_year = employee.date_of_joining.strftime("%Y")
            today = datetime.today()
            current_year = today.strftime("%Y")
            year_complete = int(current_year) - int(anniversary_year)
            employee_anni_dic[employee] = year_complete

        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_anniversary_data_tbl', {'employee_anni_dic': employee_anni_dic, 'todays_date': todays_date})
