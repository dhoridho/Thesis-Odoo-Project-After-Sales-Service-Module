# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from datetime import timedelta, datetime, date
from ...sh_hr_dashboard.controllers.main import HRDashboard
import pytz
from odoo import fields
from collections import OrderedDict
import calendar


class Equip3HrDashboardExtend(http.Controller):

    @http.route('/get_hr_annoucement_data', type='http', auth="public", methods=['GET'])
    def get_annoucement_data(self, **post):
        current_user = request.session.uid
        announcements = request.env['hr.announcement'].sudo().search(
            [('state', '=', 'submitted'), ('email_employee_ids.user_id', '=', current_user)], order='date_start')
        return request.env['ir.ui.view'].with_context()._render_template(
            'equip3_hr_dashboard_extend.hr_annoucements_data_tbl', {'annoucements': announcements})

    @http.route(['/get-popup-announcement'], type='http', auth='public')
    def get_popup_announcement(self, **post):
        announce = request.env['hr.announcement'].sudo().browse(int(post.get('announce_id')))

        if announce:
            data = {
                'announcement_name': announce.announcement_reason,
                'date_start': str(announce.date_start.strftime('%d %B %Y')),
                'date_end': str(announce.date_end.strftime('%d %B %Y')),
                'announcement': announce.announcement
            }
            return json.dumps(data)

class HRDashboardEquip3(HRDashboard):
    @http.route('/get_employee_birhday_data', type='http', auth="public", methods=['GET'])
    def get_employee_birhday_data(self, **post):
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee and group_manager:
            employees = request.env['hr.employee'].sudo().search([])
        elif group_employee:
            employees = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
        elif group_manager:
            employee_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            employees = request.env['hr.employee'].sudo().search([('id', 'in', employee_ids)])
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
                    if (current_date >= birthdate):
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
                        days_diff = (birthdate - current_date).days
                        past_days = 0

                    if days_diff >= 0:
                        employee_birthday_dic[employee] = [days_diff]

                    if past_days >= 0:
                        if employee in employee_birthday_dic:
                            employee_birthday_dic[employee].append(past_days)
                        else:
                            employee_birthday_dic[employee] = [past_days]

        sort_employee_birthday_dic = sorted(
            employee_birthday_dic.items(), key=lambda x: (abs(x[1][0]), x[1][1]))
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_birthday_data_tbl', {
            'sort_employee_birthday_dic': sort_employee_birthday_dic})

    @http.route('/get_employee_attendance_data', type='http', auth="public", methods=['GET'])
    def get_employee_attendance_data(self, **post):
        now = datetime.now()
        group_employee = request.env.user.has_group('hr.group_hr_user') and not request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_departmen_leader')
        group_manager = request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not request.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_officer')
        if group_employee:
            attendances = request.env['hr.attendance'].sudo().search(
                [('employee_id.user_id', '=', request.env.user.id)], limit=10)
        elif group_manager:
            last_week_start, last_week_end = self.previous_week_range(now.date())
            employee_ids = []
            attendance_ids = []
            my_employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            attendances_list = request.env['hr.attendance'].sudo().search(
                [('employee_id', 'in', employee_ids)], limit=50, order='start_working_date desc')
            attendance_ids.extend(data_attendance.id for data_attendance in attendances_list if
                                  data_attendance.start_working_date >= last_week_start and data_attendance.start_working_date <= now.date())
            attendances = request.env['hr.attendance'].sudo().browse(attendance_ids)
        else:
            attendances = request.env['hr.attendance'].sudo().search(
                [], limit=10)
        attendance_dic = {}
        for attendance in attendances:
            data_list = []
            # get the user's timezone
            user_timezone = pytz.timezone(request.env.context.get('tz') or 'UTC')
            if attendance.check_in:
                # convert the check_in field to a timezone-aware datetime object
                check_in = fields.Datetime.from_string(attendance.check_in).replace(tzinfo=pytz.utc).astimezone(user_timezone)
                data_list.append(check_in)
            else:
                data_list.append('')

            if attendance.check_out:
                # convert the check_out field to a timezone-aware datetime object
                check_out = fields.Datetime.from_string(attendance.check_out).replace(tzinfo=pytz.utc).astimezone(user_timezone)
                data_list.append(check_out)
            else:
                data_list.append('')

            attendance_dic[attendance] = data_list
        return request.env['ir.ui.view'].with_context()._render_template('sh_hr_dashboard.sh_attendance_data_tbl',
                                                                         {'attendance_dic': attendance_dic})

class OnboardingController(http.Controller):

    @http.route('/director_dashboard/fetch_dashboard_data', type="json", auth='user')
    def director_dashboard_fetch_dashboard_data(self, **post):
        filter_year = filter_semester = filter_monthly = filter_quarterly = graph_1_filter = graph_2_filter = graph_3_filter = graph_4_filter = False
        if post.get('graph_arr'):
            if 'graph_1' in post['graph_arr']:
                graph_1_filter = True
            if 'graph_2' in post['graph_arr']:
                graph_2_filter = True
            if 'graph_3' in post['graph_arr']:
                graph_3_filter = True
            if 'graph_4' in post['graph_arr']:
                graph_4_filter = True

        pie_1_data = [] 
        pie_2_data = []
        pie_3_data = []
        bar_4_data = []
        pivot_4_data = {}

        if post.get('filter') == 'yearly_graph_1':
            filter_year = post.get('value')
        if post.get('filter') == 'semesterly_graph_1':
            filter_semester = post.get('value')
        if post.get('filter') == 'yearly_graph_3':
            filter_year = post.get('value')
        if post.get('filter') == 'semesterly_graph_3':
            filter_semester = post.get('value')
        if 'monthly_2_graph' in post.get('filter'):
            filter_monthly = post.get('value')
        if post.get('filter') == 'yearly_graph_4':
            filter_year = post.get('value')
        if post.get('filter') == 'quarterly_graph_4':
            filter_quarterly = post.get('value')
        
        if graph_1_filter:
            hr_contract_obj = request.env['hr.contract'].sudo().search([('state', 'in', ['open'])])
            on_going_contract = expire_this_period_contract = 0
            for contract in hr_contract_obj:
                if contract.date_end and filter_year:
                    filter_year = int(filter_year)
                    if contract.date_end.year == filter_year:
                        expire_this_period_contract += 1
                    elif contract.date_end.year > filter_year:
                        on_going_contract += 1
                elif contract.date_end and filter_semester:
                    semester = filter_semester.split(' ')[0]
                    year = int(filter_semester.split(' ')[1])
                    if semester == '1st':
                        if contract.date_end.month <= 6 and contract.date_end.year == year:
                            expire_this_period_contract += 1
                        elif contract.date_end.month > 6 and contract.date_end.year == year:
                            on_going_contract += 1
                        elif contract.date_end.year > year:
                            on_going_contract += 1
                    else:
                        if contract.date_end.month > 6 and contract.date_end.year == year:
                            expire_this_period_contract += 1
                        else:
                            on_going_contract += 1
                elif contract.date_end and filter_monthly:
                    month = filter_monthly.split(' ')[0]
                    year = int(filter_monthly.split(' ')[1])
                    month_num = datetime.strptime(month, '%B').month

                    if contract.date_end.month == month_num and contract.date_end.year == year:
                        expire_this_period_contract += 1
                    elif contract.date_end.month > month_num and contract.date_end.year == year:
                        on_going_contract += 1
                    elif contract.date_end.year > year:
                        on_going_contract += 1
                else:
                    on_going_contract += 1

            if on_going_contract:
                value = {'contract_state': 'On Going Contract', 'qty': on_going_contract}
                pie_1_data.append(value)
            if expire_this_period_contract:
                value = {'contract_state': 'Will Expire in This Period', 'qty': expire_this_period_contract}
                pie_1_data.append(value)

        if graph_2_filter:
            last_30_days = date.today() - timedelta(days=30)
            hr_employee_obj = request.env['hr.employee'].sudo().search([('date_of_joining', '>', last_30_days)])
            for employee in hr_employee_obj:
                for contract in employee.contract_line_ids:
                    if contract.state == 'open':
                        job_position = contract.job_id.name
                        if pie_2_data:
                            job_data_exist = False
                            for data in pie_2_data:
                                if data.get('job_position') == job_position:
                                    data['qty'] += 1
                                    job_data_exist = True
                            if not job_data_exist:
                                value = {'job_position': job_position, 'qty': 1}
                                pie_2_data.append(value)
                        else:
                            value = {'job_position': job_position, 'qty': 1}
                            pie_2_data.append(value)

        current_datetime = datetime.today()

        if graph_3_filter:
            hr_leave_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate')])
            for leave in hr_leave_obj:
                if leave.date_from >= current_datetime:
                    if leave.date_from and filter_year:
                        filter_year = int(filter_year)
                        if leave.date_from.year == filter_year:
                            for contract in leave.employee_id.contract_line_ids:
                                if contract.state == 'open':
                                    department_name = contract.department_id.name
                                    if pie_3_data:
                                        job_data_exist = False
                                        for data in pie_3_data:
                                            if data.get('department_name') == department_name:
                                                data['qty'] += 1
                                                job_data_exist = True
                                        if not job_data_exist:
                                            value = {'department_name': department_name, 'qty': 1}
                                            pie_3_data.append(value)
                                    else:
                                        value = {'department_name': department_name, 'qty': 1}
                                        pie_3_data.append(value)
                    elif leave.date_from and filter_semester:
                        semester = filter_semester.split(' ')[0]
                        year = int(filter_semester.split(' ')[1])

                        if semester == '1st':
                            if leave.date_from.month <= 6 and leave.date_from.year == year:
                                for contract in leave.employee_id.contract_line_ids:
                                    if contract.state == 'open':
                                        department_name = contract.department_id.name
                                        if pie_3_data:
                                            job_data_exist = False
                                            for data in pie_3_data:
                                                if data.get('department_name') == department_name:
                                                    data['qty'] += 1
                                                    job_data_exist = True
                                            if not job_data_exist:
                                                value = {'department_name': department_name, 'qty': 1}
                                                pie_3_data.append(value)
                                        else:
                                            value = {'department_name': department_name, 'qty': 1}
                                            pie_3_data.append(value)
                        else:
                            if leave.date_from.month > 6 and leave.date_from.year == year:
                                for contract in leave.employee_id.contract_line_ids:
                                    if contract.state == 'open':
                                        department_name = contract.department_id.name
                                        if pie_3_data:
                                            job_data_exist = False
                                            for data in pie_3_data:
                                                if data.get('department_name') == department_name:
                                                    data['qty'] += 1
                                                    job_data_exist = True
                                            if not job_data_exist:
                                                value = {'department_name': department_name, 'qty': 1}
                                                pie_3_data.append(value)
                                        else:
                                            value = {'department_name': department_name, 'qty': 1}
                                            pie_3_data.append(value)
                    elif leave.date_from and filter_monthly:
                        month = filter_monthly.split(' ')[0]
                        year = int(filter_monthly.split(' ')[1])
                        month_num = datetime.strptime(month, '%B').month

                        if leave.date_from.month == month_num and leave.date_from.year == year:
                            for contract in leave.employee_id.contract_line_ids:
                                if contract.state == 'open':
                                    department_name = contract.department_id.name
                                    if pie_3_data:
                                        job_data_exist = False
                                        for data in pie_3_data:
                                            if data.get('department_name') == department_name:
                                                data['qty'] += 1
                                                job_data_exist = True
                                        if not job_data_exist:
                                            value = {'department_name': department_name, 'qty': 1}
                                            pie_3_data.append(value)
                                    else:
                                        value = {'department_name': department_name, 'qty': 1}
                                        pie_3_data.append(value)

        if graph_4_filter:
            department_list = []
            hr_overtime_obj = request.env['hr.overtime.actual'].sudo().search([('state','=','approved'),('total_actual_hours','>',0)])

            if filter_year:
                year_list = []
                today_year = (datetime.today()).year
                
                today_year -= 5
                for i in range(5):
                    today_year += 1
                    year_list.append(today_year)

                for overtime in hr_overtime_obj:
                    if overtime.period_start.year in year_list:
                        child_dept = overtime.employee_id.department_id.name or False
                        parent_dept = overtime.employee_id.department_id.parent_id.name or False
                        parent_exist = False

                        for dept in department_list:
                            if parent_dept:
                                if dept['parent'] == parent_dept:
                                    parent_exist = True
                                    child_exist = False
                                    
                                    for child in dept['child']:
                                        if child_dept in dept['child']:
                                            child_exist = True

                                    if not child_exist:
                                        dept['child'].append(child_dept)
                                        
                            elif child_dept:
                                if dept['parent'] == child_dept:
                                    parent_exist = True
                                    child_exist = False

                                    for child in dept['child']:
                                        if child_dept in dept['child']:
                                            child_exist = True

                                    if not child_exist:
                                        dept['child'].append(child_dept)


                        if not parent_exist:
                            if parent_dept:
                                dept_value = {'parent': parent_dept, 'child': []}
                            else:
                                dept_value = {'parent': child_dept, 'child': [child_dept]}

                            department_list.append(dept_value)

                for year in year_list:
                    value = {
                        'period': year, 
                        'hours': 0,
                        'pivot_hours_data': []
                    }

                    for overtime in hr_overtime_obj:
                        if overtime.period_start.year == year:
                            value['hours'] += overtime.total_actual_hours

                    for dept in department_list:
                        for child_dept in dept['child']:
                            total_hours = 0
                            for overtime in hr_overtime_obj:
                                if overtime.period_start.year == year and overtime.employee_id.department_id.name == child_dept:
                                    total_hours += overtime.total_actual_hours
                            
                            if total_hours == 0: total_hours = '-'
                            value['pivot_hours_data'].append(total_hours)

                    bar_4_data.append(value)

            elif filter_quarterly:
                filter_quarterly = int(filter_quarterly)
                bar_4_data = [
                    {'period': 'Q1', 'hours': 0, 'pivot_hours_data': []},
                    {'period': 'Q2', 'hours': 0, 'pivot_hours_data': []},
                    {'period': 'Q3', 'hours': 0, 'pivot_hours_data': []},
                    {'period': 'Q4', 'hours': 0, 'pivot_hours_data': []},
                ]

                for overtime in hr_overtime_obj:
                    if overtime.period_start.year == filter_quarterly:
                        if overtime.period_start.month in [1,2,3]:
                            for data in bar_4_data:
                                if data['period'] == 'Q1':
                                    data['hours'] += overtime.total_actual_hours
                        elif overtime.period_start.month in [4,5,6]:
                            for data in bar_4_data:
                                if data['period'] == 'Q2':
                                    data['hours'] += overtime.total_actual_hours
                        elif overtime.period_start.month in [7,8,9]:
                            for data in bar_4_data:
                                if data['period'] == 'Q3':
                                    data['hours'] += overtime.total_actual_hours
                        elif overtime.period_start.month in [10,11,12]:
                            for data in bar_4_data:
                                if data['period'] == 'Q4':
                                    data['hours'] += overtime.total_actual_hours

                for data in bar_4_data:
                    for overtime in hr_overtime_obj:
                        if overtime.period_start.year == filter_quarterly:
                            child_dept = overtime.employee_id.department_id.name or False
                            parent_dept = overtime.employee_id.department_id.parent_id.name or False
                            parent_exist = False

                            for dept in department_list:
                                if parent_dept:
                                    if dept['parent'] == parent_dept:
                                        parent_exist = True
                                        child_exist = False
                                        
                                        for child in dept['child']:
                                            if child_dept in dept['child']:
                                                child_exist = True

                                        if not child_exist:
                                            dept['child'].append(child_dept)
                                            
                                elif child_dept:
                                    if dept['parent'] == child_dept:
                                        parent_exist = True
                                        child_exist = False
                                        
                                        for child in dept['child']:
                                            if child_dept in dept['child']:
                                                child_exist = True

                                        if not child_exist:
                                            dept['child'].append(child_dept)

                            if not parent_exist:
                                if parent_dept:
                                    dept_value = {'parent': parent_dept, 'child': []}
                                else:
                                    dept_value = {'parent': child_dept, 'child': [child_dept]}

                                department_list.append(dept_value)

                    for dept in department_list:
                        for child_dept in dept['child']:
                            total_hours = 0
                            for overtime in hr_overtime_obj:
                                if overtime.period_start.year == filter_quarterly:
                                    if data['period'] == 'Q1' and overtime.period_start.month in [1,2,3]:
                                        if overtime.employee_id.department_id.name == child_dept:
                                            total_hours += overtime.total_actual_hours
                                    elif data['period'] == 'Q2' and overtime.period_start.month in [4,5,6]:
                                        if overtime.employee_id.department_id.name == child_dept:
                                            total_hours += overtime.total_actual_hours
                                    elif data['period'] == 'Q3' and overtime.period_start.month in [7,8,9]:
                                        if overtime.employee_id.department_id.name == child_dept:
                                            total_hours += overtime.total_actual_hours
                                    elif data['period'] == 'Q4' and overtime.period_start.month in [10,11,12]:
                                        if overtime.employee_id.department_id.name == child_dept:
                                            total_hours += overtime.total_actual_hours
                            
                            if total_hours == 0: total_hours = '-'
                            data['pivot_hours_data'].append(total_hours)

            pivot_4_data = {'department_list': department_list}

        return {'pie_1_data': pie_1_data, 'pie_2_data': pie_2_data, 'pie_3_data': pie_3_data, 'bar_4_data': bar_4_data, 'pivot_4_data': pivot_4_data}


    @http.route('/director_dashboard/fetch_dashboard_filter', type="json", auth='user')
    def director_dashboard_fetch_dashboard_filter(self):
        yearly_filter_graph_1 = []
        yearly_filter_graph_3 = []
        semesterly_filter_graph_1 = []
        semesterly_filter_graph_3 = []
        monthly_filter_graph_1 = []
        monthly_filter_graph_3 = []
        quarterly_filter_graph_4 = []

        current_datetime = datetime.today()

        hr_contract_obj = request.env['hr.contract'].sudo().search([('state', 'in', ['open'])], order='date_end desc')
        for contract in hr_contract_obj:
            if contract.date_end:
                if contract.date_end.year not in yearly_filter_graph_1:
                    yearly_filter_graph_1.append(contract.date_end.year)

                if contract.date_end.month > 6:
                    semesterly_filter_graph_1.append("2nd %s" % contract.date_end.year)
                else:
                    semesterly_filter_graph_1.append("1st %s" % contract.date_end.year)

                monthly_desc = calendar.month_name[contract.date_end.month] + ' ' + str(contract.date_end.year)

                if monthly_desc not in monthly_filter_graph_1:
                    monthly_filter_graph_1.append(monthly_desc)

        hr_leave_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate')], order='date_from desc')
        for leave in hr_leave_obj:
            if leave.date_from:
                if leave.date_from >= current_datetime:
                    for contract in leave.employee_id.contract_line_ids:
                        if contract.state == 'open':
                            if leave.date_from.year not in yearly_filter_graph_3:
                                yearly_filter_graph_3.append(leave.date_from.year)

                            if leave.date_from.month > 6:
                                semesterly_filter_graph_3.append("2nd %s" % leave.date_from.year)
                            else:
                                semesterly_filter_graph_3.append("1st %s" % leave.date_from.year)

                            monthly_desc = calendar.month_name[leave.date_from.month] + ' ' + str(leave.date_from.year)

                            if monthly_desc not in monthly_filter_graph_3:
                                monthly_filter_graph_3.append(monthly_desc)

        hr_overtime_obj = request.env['hr.overtime.actual'].sudo().search([('state','=','approved')], order='period_start desc')
        today_year = (datetime.today()).year

        for overtime in hr_overtime_obj:
            if overtime.period_start.year <= today_year:
                if overtime.period_start.year not in quarterly_filter_graph_4:
                    quarterly_filter_graph_4.append(overtime.period_start.year)

        semesterly_filter_graph_1 = list(OrderedDict.fromkeys(semesterly_filter_graph_1))
        semesterly_filter_graph_3 = list(OrderedDict.fromkeys(semesterly_filter_graph_3))

        return {
            'yearly_filter_graph_1': yearly_filter_graph_1, 
            'semesterly_filter_graph_1': semesterly_filter_graph_1,
            'monthly_filter_graph_1': monthly_filter_graph_1,
            'yearly_filter_graph_3': yearly_filter_graph_3,
            'semesterly_filter_graph_3': semesterly_filter_graph_3,
            'monthly_filter_graph_3': monthly_filter_graph_3,
            'quarterly_filter_graph_4': quarterly_filter_graph_4,
            }


    @http.route('/hr_operational_dashboard/fetch_dashboard_filter', type="json", auth='user')
    def hr_operational_dashboard_fetch_dashboard_filter(self):
        filter_graph_1 = []

        today_year = (datetime.today()).year
        hr_leave_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False)], order='request_date_from desc')

        for leave in hr_leave_obj:
            if leave.request_date_from:
                if leave.request_date_from.year in range((today_year - 4), (today_year + 1)): # 5 years range (2019, 2023)
                    if leave.request_date_from.year not in filter_graph_1:
                        filter_graph_1.append(leave.request_date_from.year)

        return {
            'filter_graph_1': filter_graph_1,
            }


    @http.route('/hr_operational_dashboard/fetch_dashboard_data', type="json", auth='user')
    def hr_operational_dashboard_fetch_dashboard_data(self, **post):
        filter_year = filter_monthly = filter_quarterly = filter_days = graph_1_filter = False
        if post.get('graph_arr'):
            if 'graph_1' in post['graph_arr']:
                graph_1_filter = True
        
        graph_1_data = []
        leave_type_list = []

        if post.get('filter') == 'yearly_graph_1':
            filter_year = post.get('value')
        if post.get('filter') == 'quarterly_graph_1':
            filter_quarterly = post.get('value')
        if post.get('filter') == 'monthly_graph_1':
            filter_monthly = post.get('value')
        if post.get('filter') == 'days_graph_1':
            filter_days = post.get('value')

        if graph_1_filter:
            hr_leave_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','!=',False)])

            if filter_year:
                year_list = []
                today_year = (datetime.today()).year
                
                today_year -= 5
                for i in range(5):
                    today_year += 1
                    year_list.append(today_year)

                for leave in hr_leave_obj:
                    if leave.request_date_from.year in year_list:
                        leave_exist = False

                        for data in leave_type_list:
                            if leave.holiday_status_id.id == data['leave_type_id']:
                                leave_exist = True
                                break

                        if not leave_exist:
                            value = {'leave_type_name': leave.holiday_status_id.name, 'leave_type_id': leave.holiday_status_id.id, 'department_list': []}
                            leave_type_list.append(value)

                for data in leave_type_list:
                    hr_leave_holiday_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','=',data['leave_type_id'])])

                    for leave in hr_leave_holiday_obj:
                        if leave.request_date_from.year in year_list:
                            if leave.department_id.name not in data['department_list']:
                                data['department_list'].append(leave.department_id.name)

                for year in year_list:
                    value = {
                        'period': year,
                        'pivot_total_data': []
                    }

                    for data in leave_type_list:
                        total_period_data = 0
                        
                        hr_leave_type_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','!=',False),('holiday_status_id','=',data['leave_type_id'])])
                        for leave in hr_leave_type_obj:
                            if leave.request_date_from.year == year:
                                total_period_data += 1

                        if total_period_data == 0: total_period_data = '-'
                        value['pivot_total_data'].append(total_period_data)

                        for dept in data['department_list']:
                            total_dept_data = 0

                            hr_leave_dept_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','=',dept),('holiday_status_id','=',data['leave_type_id'])])
                            for leave in hr_leave_dept_obj:
                                if leave.request_date_from.year == year:
                                    total_dept_data += 1

                            if total_dept_data == 0: total_dept_data = '-'
                            value['pivot_total_data'].append(total_dept_data)

                    graph_1_data.append(value)

            elif filter_quarterly:
                quarter_list = ['Q1', 'Q2', 'Q3', 'Q4']
                selected_year = int(filter_quarterly)

                for leave in hr_leave_obj:
                    if leave.request_date_from.year == selected_year:
                        leave_exist = False

                        for data in leave_type_list:
                            if leave.holiday_status_id.id == data['leave_type_id']:
                                leave_exist = True
                                break

                        if not leave_exist:
                            value = {'leave_type_name': leave.holiday_status_id.name, 'leave_type_id': leave.holiday_status_id.id, 'department_list': []}
                            leave_type_list.append(value)

                for data in leave_type_list:
                    hr_leave_holiday_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','=',data['leave_type_id'])])

                    for leave in hr_leave_holiday_obj:
                        if leave.request_date_from.year == selected_year:
                            if leave.department_id.name not in data['department_list']:
                                data['department_list'].append(leave.department_id.name)

                for quarter in quarter_list:
                    value = {
                        'period': quarter,
                        'pivot_total_data': []
                    }

                    for data in leave_type_list:
                        total_period_data = 0
                        
                        hr_leave_type_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','!=',False),('holiday_status_id','=',data['leave_type_id'])])
                        for leave in hr_leave_type_obj:
                            if leave.request_date_from.year == selected_year:
                                if quarter == 'Q1' and leave.request_date_from.month in [1,2,3]:
                                    total_period_data += 1
                                elif quarter == 'Q2' and leave.request_date_from.month in [4,5,6]:
                                    total_period_data += 1
                                elif quarter == 'Q3' and leave.request_date_from.month in [7,8,9]:
                                    total_period_data += 1
                                elif quarter == 'Q4' and leave.request_date_from.month in [10,11,12]:
                                    total_period_data += 1

                        if total_period_data == 0: total_period_data = '-'
                        value['pivot_total_data'].append(total_period_data)

                        for dept in data['department_list']:
                            total_dept_data = 0

                            hr_leave_dept_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','=',dept),('holiday_status_id','=',data['leave_type_id'])])
                            for leave in hr_leave_dept_obj:
                                if leave.request_date_from.year == selected_year:
                                    if quarter == 'Q1' and leave.request_date_from.month in [1,2,3]:
                                        total_dept_data += 1
                                    elif quarter == 'Q2' and leave.request_date_from.month in [4,5,6]:
                                        total_dept_data += 1
                                    elif quarter == 'Q3' and leave.request_date_from.month in [7,8,9]:
                                        total_dept_data += 1
                                    elif quarter == 'Q4' and leave.request_date_from.month in [10,11,12]:
                                        total_dept_data += 1

                            if total_dept_data == 0: total_dept_data = '-'
                            value['pivot_total_data'].append(total_dept_data)

                    graph_1_data.append(value)

            elif filter_monthly:
                month_list = calendar.month_name[1:]
                selected_year = int(filter_monthly)

                for leave in hr_leave_obj:
                    if leave.request_date_from.year == selected_year:
                        leave_exist = False

                        for data in leave_type_list:
                            if leave.holiday_status_id.id == data['leave_type_id']:
                                leave_exist = True
                                break

                        if not leave_exist:
                            value = {'leave_type_name': leave.holiday_status_id.name, 'leave_type_id': leave.holiday_status_id.id, 'department_list': []}
                            leave_type_list.append(value)

                for data in leave_type_list:
                    hr_leave_holiday_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','=',data['leave_type_id'])])

                    for leave in hr_leave_holiday_obj:
                        if leave.request_date_from.year == selected_year:
                            if leave.department_id.name not in data['department_list']:
                                data['department_list'].append(leave.department_id.name)

                for month_data in month_list:
                    value = {
                        'period': month_data,
                        'pivot_total_data': []
                    }

                    month_num = datetime.strptime(month_data, '%B').month

                    for data in leave_type_list:
                        total_period_data = 0
                        
                        hr_leave_type_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','!=',False),('holiday_status_id','=',data['leave_type_id'])])
                        for leave in hr_leave_type_obj:
                            if leave.request_date_from.year == selected_year and leave.request_date_from.month == month_num:
                                total_period_data += 1

                        if total_period_data == 0: total_period_data = '-'
                        value['pivot_total_data'].append(total_period_data)

                        for dept in data['department_list']:
                            total_dept_data = 0

                            hr_leave_dept_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','=',dept),('holiday_status_id','=',data['leave_type_id'])])
                            for leave in hr_leave_dept_obj:
                                if leave.request_date_from.year == selected_year and leave.request_date_from.month == month_num:
                                    total_dept_data += 1

                            if total_dept_data == 0: total_dept_data = '-'
                            value['pivot_total_data'].append(total_dept_data)

                    graph_1_data.append(value)

            elif filter_days:
                today = datetime.today()
                date_list = []

                if filter_days == 'last_7_days':
                    days_count = 6
                    for i in range(7):
                        date_range = today - timedelta(days=days_count)
                        date_list.append(date_range)
                        days_count -= 1
                else:
                    days_count = 0
                    for i in range(7):
                        date_range = today + timedelta(days=days_count)
                        date_list.append(date_range)
                        days_count += 1

                hr_leave_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','!=',False),('request_date_from','in',date_list)])
                for leave in hr_leave_obj:
                    leave_exist = False

                    for data in leave_type_list:
                        if leave.holiday_status_id.id == data['leave_type_id']:
                            leave_exist = True
                            break

                    if not leave_exist:
                        value = {'leave_type_name': leave.holiday_status_id.name, 'leave_type_id': leave.holiday_status_id.id, 'department_list': []}
                        leave_type_list.append(value)

                for data in leave_type_list:
                    hr_leave_holiday_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id','!=',False),('holiday_status_id','=',data['leave_type_id']),('request_date_from','in',date_list)])

                    for leave in hr_leave_holiday_obj:
                        if leave.department_id.name not in data['department_list']:
                            data['department_list'].append(leave.department_id.name)

                for date_data in date_list:
                    value = {
                        'period': calendar.day_name[date_data.weekday()],
                        'pivot_total_data': []
                    }

                    for data in leave_type_list:
                        total_period_data = 0
                        
                        hr_leave_type_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','!=',False),('holiday_status_id','=',data['leave_type_id']),('request_date_from','=',date_data)])
                        for leave in hr_leave_type_obj:
                            total_period_data += 1

                        if total_period_data == 0: total_period_data = '-'
                        value['pivot_total_data'].append(total_period_data)

                        for dept in data['department_list']:
                            total_dept_data = 0

                            hr_leave_dept_obj = request.env['hr.leave'].sudo().search([('state', '=', 'validate'),('department_id.name','=',dept),('holiday_status_id','=',data['leave_type_id']),('request_date_from','=',date_data)])
                            for leave in hr_leave_dept_obj:
                                total_dept_data += 1

                            if total_dept_data == 0: total_dept_data = '-'
                            value['pivot_total_data'].append(total_dept_data)

                    graph_1_data.append(value)

        leave_type_data = {'leave_type_list': leave_type_list}

        return {'graph_1_data': graph_1_data, 'leave_type_data': leave_type_data}

    @http.route('/hr_operational_dashboard/fetch_attendance_data', type="json", auth='user')
    def hr_operational_dashboard_fetch_attendance_data(self, **post):
        attendance_data = []
        HrAttendance = request.env['hr.attendance'].search([('start_working_date','=',date.today()),('attendance_status','in',post.get('status'))], order='sequence_code asc')
        for attendance in HrAttendance:
            attendance_data.append({
                'employee_name': attendance.employee_id.name,
                'employee_id': attendance.sequence_code,
                'department': attendance.department_id.name,
                'attendance_status': attendance.attendance_status.capitalize(),
                'leave_type': attendance.leave_type.name or '-',
                'working_date': attendance.start_working_date.strftime("%m/%d/%Y"),
                'check_in': attendance.check_in,
                'attendance_id': attendance.id,
            })
        return {'attendance_data': attendance_data}