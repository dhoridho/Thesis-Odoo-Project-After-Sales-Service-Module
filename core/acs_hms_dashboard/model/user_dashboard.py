# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import time

import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from babel.dates import format_datetime, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools.misc import formatLang
from odoo.release import version


class ResUsers(models.Model):
    _inherit = "res.users"

    def get_filter(self, field_name):
        for rec in self:
            domain = []
            if rec.dashboard_data_filter=='today':
                domain = [(field_name, '>=', time.strftime('%Y-%m-%d 00:00:00')),(field_name, '<=', time.strftime('%Y-%m-%d 23:59:59'))]
            if rec.dashboard_data_filter=='week':
                domain = [(field_name, '>=', (fields.Datetime.today() + relativedelta(weeks=-1,days=1,weekday=0)).strftime('%Y-%m-%d')), (field_name, '<=', (fields.Datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d'))]
            if rec.dashboard_data_filter=='month':
                domain = [(field_name,'<',(fields.Datetime.today()+relativedelta(months=1)).strftime('%Y-%m-01')), (field_name,'>=',time.strftime('%Y-%m-01'))]
        return domain
        
    @api.depends('dashboard_data_filter')
    def _compute_dashboard_data(self):
        #Patients
        Patient = self.env['hms.patient']
        patient_domain = self.get_filter('create_date')
        self.total_patients = Patient.search_count(patient_domain)
        patient_domain += [('primary_doctor.user_id','=',self.env.uid)]
        self.my_total_patients = Patient.search_count(patient_domain)

        #Physicians
        Physician = self.env['hms.physician']
        Partner = self.env['res.partner']
        physicians_domain = self.get_filter('create_date')
        self.total_physicians = Physician.search_count(physicians_domain)
        ref_physicians_domain = self.get_filter('create_date')
        ref_physicians_domain += [('is_referring_doctor','=',True)]
        self.total_referring_physicians = Partner.search_count(ref_physicians_domain)

        #Schedules
        Shedules = self.env['resource.calendar']
        self.total_shedules = Shedules.search_count([])

        #Appointments
        Appointment = self.env['hms.appointment']
        appointment_domain = self.get_filter('date')
        self.total_appointments = Appointment.search_count(appointment_domain)
        self.my_total_appointments =  Appointment.search_count(appointment_domain+[('physician_id.user_id','=',self.env.uid)])

        appointmnt_data = []
        if self.is_physician:
            appointment_list = Appointment.search(appointment_domain+[('physician_id.user_id','=',self.env.uid)], limit=20)
        else:
            appointment_list = Appointment.search(appointment_domain, limit=20)

        for appointment in appointment_list:
            app_date = appointment.date.strftime(DTF)
            appointmnt_data.append({
                'name': appointment.name,                  
                'patient': appointment.patient_id.name,
                'date': app_date or '',
                'physician': appointment.physician_id.name,
                'waiting_duration': '{0:02.0f}:{1:02.0f}'.format(*divmod(appointment.waiting_duration * 60, 60)),
                'appointment_duration': '{0:02.0f}:{1:02.0f}'.format(*divmod(appointment.appointment_duration * 60, 60)),
                'state': dict(appointment._fields['state']._description_selection(self.env)).get(appointment.state),
            })
        self.appointment_data = json.dumps(appointmnt_data)

        #My Avg Time
        my_appointments_domain = self.get_filter('date')
        my_appointments_domain += [('physician_id.user_id','=',self.env.uid)]
        my_total_appointments = Appointment.search(my_appointments_domain)
        my_avg_cons_time = my_avg_wait_time = 0
        my_total_appointments_cnt = len(my_total_appointments)
        for app in my_total_appointments:
            my_avg_cons_time += app.appointment_duration
            my_avg_wait_time += app.waiting_duration
        my_avg_cons_time = my_avg_cons_time/my_total_appointments_cnt if my_total_appointments_cnt else 0
        self.my_avg_cons_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(my_avg_cons_time * 60, 60))
        my_avg_wait_time = my_avg_wait_time/my_total_appointments_cnt if my_total_appointments_cnt else 0
        self.my_avg_wait_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(my_avg_wait_time * 60, 60))

        #Avg Time
        total_appointments_domain = self.get_filter('date')
        total_appointments = Appointment.search(total_appointments_domain)
        avg_cons_time = avg_wait_time = 0
        total_appointments_cnt = len(total_appointments)
        self.total_appointments = total_appointments_cnt
        for app in total_appointments:
            avg_cons_time += app.appointment_duration
            avg_wait_time += app.waiting_duration
        avg_cons_time = avg_cons_time/total_appointments_cnt if total_appointments_cnt else 0
        self.avg_cons_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(avg_cons_time * 60, 60))
        avg_wait_time = avg_wait_time/total_appointments_cnt if total_appointments_cnt else 0
        self.avg_wait_time = '{0:02.0f}:{1:02.0f}'.format(*divmod(avg_wait_time * 60, 60))

        #Total Treatment
        treatment_domain = self.get_filter('date')
        Treatment = self.env['hms.treatment']
        self.total_treatments = Treatment.search_count(treatment_domain)
        running_treatment_domain = treatment_domain + [('state','=','running')]
        self.total_running_treatments = Treatment.search_count(running_treatment_domain)
        my_treatment_domain = treatment_domain + [('physician_id.user_id','=',self.env.uid)]
        self.my_total_treatments = Treatment.search_count(my_treatment_domain)
        my_running_treatment_domain = treatment_domain + [('state','=','running'), ('physician_id.user_id','=',self.env.uid)]
        self.my_total_running_treatments = Treatment.search_count(my_running_treatment_domain)

        #Open Invoices
        Invoice = self.env['account.move'].sudo()
        open_invoice_domain = self.get_filter('invoice_date')
        open_invoice_domain += [('move_type','=','out_invoice'),('state','=','posted')]
        open_invoice = Invoice.search(open_invoice_domain)
        self.total_open_invoice = len(open_invoice)
        total = 0
        for inv in open_invoice:
            total += inv.amount_residual
        self.total_open_invoice_amount =total

        #Birthday
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        self.birthday_patients = Patient.search_count([('birthday', 'like', today_month_day)])
        self.birthday_employee = self.env['hr.employee'].search_count([('birthday', 'like', today_month_day)])

        self.appointment_bar_graph = json.dumps(self.get_bar_graph_datas())
        self.patient_line_graph = json.dumps(self.get_line_graph_datas())

    dashboard_data_filter = fields.Selection([
            ('today','Today'),
            ('week','This Week'),
            ('month','This Month'),
            ('year','This Year'),
            ('all','All'),
        ], "Dashboard Filter Type", default="today")

    birthday_patients = fields.Integer(compute="_compute_dashboard_data")
    birthday_employee = fields.Integer(compute="_compute_dashboard_data")
    birthday_color = fields.Char(string='Birthday Color', default="#5cb85c")

    #Receptionist Dashboard fields
    total_patients = fields.Integer(compute="_compute_dashboard_data")
    total_patients_color = fields.Char(string='Total Patient Color', default="#0B9EBA")
    total_running_treatments = fields.Integer(compute="_compute_dashboard_data")
    total_treatments = fields.Integer(compute="_compute_dashboard_data")
    total_treatments_color = fields.Char(string='Total Treatments Color', default="#5cb85c")

    total_appointments = fields.Integer(compute="_compute_dashboard_data")
    total_appointments_color = fields.Char(string='Total Appointments Color', default="#f0ad4e")
    
    total_open_invoice = fields.Integer(compute="_compute_dashboard_data")
    total_open_invoice_amount = fields.Integer(compute="_compute_dashboard_data")
    total_open_invoice_color = fields.Char(string='Open Invoices', default="#d9534f")

    total_shedules = fields.Integer(compute="_compute_dashboard_data")
    total_shedules_color = fields.Char(string='Total Shedules Color', default="#6200FF")

    appointment_bar_graph = fields.Text(compute='_compute_dashboard_data')
    appointment_bar_graph_color = fields.Char(string='Patient Barchart Color', default="#0B9EBA")
    patient_line_graph = fields.Text(compute='_compute_dashboard_data')
    patient_line_graph_color = fields.Char(string='Patient Linechart Color', default="#6200FF")

    appointment_data = fields.Text(string="Patient Appointments", compute="_compute_dashboard_data")

    #Nurse Dashboard fields

    #Doctor Fields
    my_total_patients = fields.Integer(compute="_compute_dashboard_data")
    my_total_patients_color = fields.Char(string='My Total Patient Color', default="#0B9EBA")
    my_total_appointments = fields.Integer(compute="_compute_dashboard_data")
    my_total_appointments_color = fields.Char(string='My Total Appointments Color', default="#f0ad4e")
    my_avg_wait_time = fields.Char(compute="_compute_dashboard_data")
    my_avg_cons_time = fields.Char(compute="_compute_dashboard_data")
    my_avg_time_color = fields.Char(string='My Avg Time Color', default="#6200FF")
    
    my_total_treatments = fields.Integer(compute="_compute_dashboard_data")
    my_total_running_treatments = fields.Integer(compute="_compute_dashboard_data")
    my_total_treatments_color = fields.Char(string='My Total Treatments Color', default="#5cb85c")

    #Admin fields 
    total_appointments = fields.Integer(compute="_compute_dashboard_data")
    avg_wait_time = fields.Char(compute="_compute_dashboard_data")
    avg_cons_time = fields.Char(compute="_compute_dashboard_data")
    avg_time_color = fields.Char( string='Avg Time Color', default="#6200FF")
    total_physicians = fields.Integer(compute="_compute_dashboard_data")
    total_referring_physicians = fields.Integer(compute="_compute_dashboard_data")
    physicians_color = fields.Char(string='Total Physicians Color', default="#0B9EBA")

    def _get_user_role(self):
        for rec in self:
            rec.is_physician = True if (rec.physician_count > 0) else False
            rec.is_manager = rec.has_group('acs_hms_base.group_hms_manager')

    is_physician = fields.Boolean(compute='_get_user_role', string="Is Physician", readonly=True)
    is_manager = fields.Boolean(compute='_get_user_role', string="Is Manager", readonly=True)

    def get_bar_graph_datas(self):
        data = []
        today = fields.Datetime.now()
        data.append({'label': _('Past'), 'value':0.0, 'type': 'past'})
        day_of_week = int(format_datetime(today, 'e', locale=self._context.get('lang') or 'en_US'))
        first_day_of_week = today + timedelta(days=-day_of_week+1)
        for i in range(-1,4):
            if i==0:
                label = _('This Week')
            elif i==3:
                label = _('Future')
            else:
                start_week = first_day_of_week + timedelta(days=i*7)
                end_week = start_week + timedelta(days=6)
                if start_week.month == end_week.month:
                    label = str(start_week.day) + '-' +str(end_week.day)+ ' ' + format_date(end_week, 'MMM', locale=self._context.get('lang') or 'en_US')
                else:
                    label = format_date(start_week, 'd MMM', locale=self._context.get('lang') or 'en_US')+'-'+format_date(end_week, 'd MMM', locale=self._context.get('lang') or 'en_US')
            data.append({'label':label,'value':0.0, 'type': 'past' if i<0 else 'future'})

        # Build SQL query to find amount aggregated by week
        (select_sql_clause, query_args) = ("""SELECT count(id) as total, min(date) as aggr_date
               FROM hms_appointment WHERE state != 'cancel'""",{})
        query = ''
        start_date = (first_day_of_week + timedelta(days=-7))
        for i in range(0,6):
            if i == 0:
                query += "("+select_sql_clause+" and date < '"+start_date.strftime(DF)+"')"
            elif i == 5:
                query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DF)+"')"
            else:
                next_date = start_date + timedelta(days=7)
                query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DF)+"' and date < '"+next_date.strftime(DF)+"')"
                start_date = next_date

        self.env.cr.execute(query, query_args)
        query_results = self.env.cr.dictfetchall()
        for index in range(0, len(query_results)):
            if query_results[index].get('aggr_date') != None:
                data[index]['value'] = query_results[index].get('total')

        [graph_title, graph_key] = ['', _('Appointments')]
        return [{'values': data, 'title': graph_title, 'key': graph_key}]

    def get_line_graph_datas(self):
        data = []
        today = fields.Date.today()
        last_month = today + timedelta(days=-30)
        data_stmt = []
        # Query to optimize loading of data for bank graphs
        # last 30 days
        query = """SELECT count(id) as total, create_date::timestamp::date as date
               FROM hms_patient WHERE create_date > %s
                                    AND create_date <= %s
                                    GROUP BY create_date::timestamp::date
                                    ORDER BY create_date::timestamp::date"""
 
        self.env.cr.execute(query, (last_month, today))
        data_stmt = self.env.cr.dictfetchall()

        locale = self._context.get('lang') or 'en_US'
        show_date = last_month
        #get date in locale format
        name = format_date(show_date, 'd LLLL Y', locale=locale)
        short_name = format_date(show_date, 'd MMM', locale=locale)
        data.append({'x':short_name,'y':0, 'name':name})

        for stmt in data_stmt:
            #fill the gap between last data and the new one
            number_day_to_add = (stmt.get('date') - show_date).days
            last_balance = data[len(data) - 1]['y']
            for day in range(0,number_day_to_add + 1):
                show_date = show_date + timedelta(days=1)
                #get date in locale format
                name = format_date(show_date, 'd LLLL Y', locale=locale)
                short_name = format_date(show_date, 'd MMM', locale=locale)
                data.append({'x': short_name, 'y':last_balance, 'name': name})
            #add new stmt value
            data[len(data) - 1]['y'] = stmt.get('total')

        #continue the graph if the last rec isn't today
        if show_date != today:
            number_day_to_add = (today - show_date).days
            last_balance = data[len(data) - 1]['y']
            for day in range(0,number_day_to_add):
                show_date = show_date + timedelta(days=1)
                #get date in locale format
                name = format_date(show_date, 'd LLLL Y', locale=locale)
                short_name = format_date(show_date, 'd MMM', locale=locale)
                data.append({'x': short_name, 'y':last_balance, 'name': name})

        [graph_title, graph_key] = ['', _('New Patients')]
        color = '#875A7B' if '+e' in version else '#7c7bad'
        return [{'values': data, 'title': graph_title, 'key': graph_key, 'area': True, 'color': color}]

    def today_data(self):
        self.sudo().dashboard_data_filter = 'today'

    def week_data(self):
        self.sudo().dashboard_data_filter = 'week'

    def month_data(self):
        self.sudo().dashboard_data_filter = 'month'

    def year_data(self):
        self.sudo().dashboard_data_filter = 'year'

    def all_data(self):
        self.sudo().dashboard_data_filter = 'all'

    def open_patients(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_patient")
        action['domain'] = self.get_filter('create_date')
        return action

    def open_my_patients(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_patient")
        action['domain'] = self.get_filter('create_date') + [('primary_doctor.user_id','=',self.env.uid)]
        return action

    def open_referring_physicians(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_referring_doctors")
        action['domain'] = self.get_filter('create_date') + [('is_referring_doctor','=',True)]
        return action

    def open_physicians(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_physician")
        action['domain'] = self.get_filter('create_date')
        return action

    def open_appointments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = self.get_filter('date')
        action['context'] = {}
        return action

    def open_treatments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = self.get_filter('date')
        action['context'] = {}
        return action

    def open_my_appointments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = self.get_filter('date') + [('physician_id.user_id','=',self.env.uid)]
        action['context'] = {}
        return action

    def open_running_treatments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = self.get_filter('date') + [('state','=','running')]
        return action

    def open_my_running_treatments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = self.get_filter('date') + [('state','=','running'),('physician_id.user_id','=',self.env.uid)]
        return action

    def open_my_treatments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = self.get_filter('date') + [('physician_id.user_id','=',self.env.uid)]
        action['context'] = {}
        return action
    
    def open_invoices(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = self.get_filter('invoice_date') + [('move_type','=','out_invoice'),('state', 'in', ['posted'])]
        return action

    def open_shedules(self):
        action = self.env["ir.actions.actions"]._for_xml_id("resource.action_resource_calendar_form")
        return action

    def open_birthday_patients(self):
        Patient = self.env['hms.patient']
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        patient_ids = Patient.search([('birthday', 'like', today_month_day)])
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_base.action_patient")
        action['domain'] = [('id','in',patient_ids.ids)]
        return action

    def open_birthday_employee(self):
        Employee = self.env['hr.employee']
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        employee_ids = Employee.search([('birthday', 'like', today_month_day)])
        action = self.env["ir.actions.actions"]._for_xml_id("hr.hr_employee_public_action")
        action['domain'] = [('id','in',employee_ids.ids)]
        return action

    def __init__(self, pool, cr):
        init_res = super(ResUsers, self).__init__(pool, cr)
        dashboard_fields = ['birthday_color', 'total_patients_color', 'total_treatments_color', 'total_appointments_color', 'total_open_invoice_color', 'total_shedules_color', 'appointment_bar_graph_color', 'patient_line_graph_color', 'my_total_patients_color', 'my_total_appointments_color', 'my_avg_time_color', 'my_total_treatments_color', 'avg_time_color', 'physicians_color']
        type(self).SELF_WRITEABLE_FIELDS = type(self).SELF_READABLE_FIELDS + dashboard_fields
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + dashboard_fields + ['is_physician','is_manager']
        return init_res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: