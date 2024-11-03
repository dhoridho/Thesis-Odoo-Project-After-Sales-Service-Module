# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
from odoo import fields, models, api
from dateutil import rrule
from datetime import timedelta
import datetime
import calendar
from dateutil.relativedelta import relativedelta
from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY

RRULE_WEEKDAY_TO_FIELD = {
    rrule.MO.weekday: 'mo',
    rrule.TU.weekday: 'tu',
    rrule.WE.weekday: 'we',
    rrule.TH.weekday: 'th',
    rrule.FR.weekday: 'fr',
    rrule.SA.weekday: 'sa',
    rrule.SU.weekday: 'su',
}

RRULE_TYPE_SELECTION = [
    ('daily', 'Days'),
    ('weekly', 'Weeks'),
    ('monthly', 'Months'),
    ('yearly', 'Years'),
]

END_TYPE_SELECTION = [
    ('count', 'Number of repetitions'),
    ('end_date', 'End date'),
]

MONTH_BY_SELECTION = [
    ('date', 'Date of month'),
    ('day', 'Day of month'),
]

WEEKDAY_SELECTION = [
    ('SU', 'Sunday'),
    ('MO', 'Monday'),
    ('TU', 'Tuesday'),
    ('WE', 'Wednesday'),
    ('TH', 'Thursday'),
    ('FR', 'Friday'),
    ('SA', 'Saturday'),
]

BYDAY_SELECTION = [
    ('1', 'First'),
    ('2', 'Second'),
    ('3', 'Third'),
    ('4', 'Fourth'),
    ('-1', 'Last'),
]


class RecurringActivities(models.Model):
    _name = 'sh.recurring.activities'
    _description = 'Helps to keep manage the recurrent Events'

    reference = fields.Reference(string='Related Document',
                                 selection='_reference_models',required="1")
    start_after_days = fields.Integer("Starts From")
    recurrency = fields.Boolean('Recurrent', help="Recurrent Activity")
    interval = fields.Integer(
        string='Repeat Every', readonly=False,
        help="Repeat every (Days/Week/Month/Year)",default="1")
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence',
                                  help="Let the Activity automatically repeat at that interval",
                                  readonly=False)
    mo = fields.Boolean('Mon', readonly=False)
    tu = fields.Boolean('Tue', readonly=False)
    we = fields.Boolean('Wed', readonly=False)
    th = fields.Boolean('Thu', readonly=False)
    fr = fields.Boolean('Fri', readonly=False)
    sa = fields.Boolean('Sat', readonly=False)
    su = fields.Boolean('Sun', readonly=False)
    month_by = fields.Selection(
        MONTH_BY_SELECTION, string='Option', readonly=False)
    day = fields.Integer(
        'Date of month', readonly=False, help="Day of Month",default='1')
    byday = fields.Selection(
        BYDAY_SELECTION, readonly=False)
    weekday = fields.Selection(
        WEEKDAY_SELECTION, readonly=False)
    month_year = fields.Selection(
        [('Jan', 'January'), ('Feb', 'February'), ('Mar', 'March'), ('Apr', 'April'), ('May', 'May'), ('Jun', 'June'), ('Jul', 'July'), ('Aug', 'August'), ('Sep', 'September'), ('Oct', 'October'), ('Nov', 'November'), ('Dec', 'December')], default='Jan')
    end_type = fields.Selection(
        END_TYPE_SELECTION, string='Recurrence Termination',readonly=False)
    count = fields.Integer(
        string='Repeat', help="Repeat x times", readonly=False)
    until = fields.Date(readonly=False)
    activity_id = fields.Many2one('mail.activity.type')
    user_id = fields.Many2one('res.users', string='Assigned to')
    summary = fields.Char("Summary")
    description = fields.Html("Note")
    mail_activities = fields.Many2many('mail.activity')

    sh_activity_tags = fields.Many2many('sh.activity.tags', string="Activity Tags")
    supervisor_id = fields.Many2one('res.users', string="Supervisor")
    sh_user_ids = fields.Many2many('res.users', string="Assign Multi User")
    sh_time_deadline = fields.Float('Remainder Time')
    sh_activity_alarm_ids = fields.Many2many('sh.activity.alarm', string="Remainders")

    @api.onchange('rrule_type')
    def onchange_rrule(self):
        self.ensure_one()
        today = fields.Date.today()
        mondays = []
        for i in range(0,2):
            next_monday = today + datetime.timedelta(days=-today.weekday(), weeks=i)
            mondays.append(next_monday)

    @api.model
    def _reference_models(self):
        models = self.env['ir.model'].sudo().search(
            [('state', '!=', 'manual')])
        return [(model.model, model.name)
                for model in models
                if not model.model.startswith('ir.')]

    def recu(self,event_starts_from):
        final_execution_date = False
        week_days_dict = {
            'Monday' : 'mo',
            'Tuesday' : 'tu',
            'Wednesday' : 'we',
            'Thursday' : 'th',
            'Friday' : 'fr',
            'Saturday' : 'sa',
            'Sunday' : 'su'
        }
        born = event_starts_from.weekday()
        born_day = calendar.day_name[born]
        if born_day == 'Sunday':
            if self.interval > 0:
                event_starts_from += datetime.timedelta(weeks=self.interval)
                event_starts_from = event_starts_from - timedelta(days=event_starts_from.weekday())
            else:
                event_starts_from += datetime.timedelta(weeks=1)
                event_starts_from = event_starts_from - timedelta(days=event_starts_from.weekday())
        else:
            event_starts_from += datetime.timedelta(days=1)
        born = event_starts_from.weekday()
        born_day = calendar.day_name[born]
        for days,short in week_days_dict.items():
            if not final_execution_date:
                if born_day == days:
                    if self['%s' % short]:
                        final_execution_date = event_starts_from
                        break
        if not final_execution_date:
            return self.recu(event_starts_from)
        else:
            return final_execution_date

    def get_month_by_date(self,final_execution_date):
        c = calendar.Calendar(firstweekday=calendar.SUNDAY)
        weekday_label = dict(WEEKDAY_SELECTION)[self.weekday]
        buu_day = int(self.byday) - 1
        if weekday_label.upper() == 'FRIDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.FRIDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'MONDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.MONDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'TUESDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.TUESDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'WEDNESDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.WEDNESDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'THURSDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.THURSDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'SATURDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SATURDAY and day.month == final_execution_date.month][buu_day]
        elif weekday_label.upper() == 'SUNDAY':
            monthcal = c.monthdatescalendar(final_execution_date.year,final_execution_date.month)
            ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SUNDAY and day.month == final_execution_date.month][buu_day]
        if ex_date:
            return ex_date

    @api.model
    def create(self,vals):
        res = super(RecurringActivities,self).create(vals)
        res.create_activity_recurring()
        return res

    def write(self,vals):
        res = super(RecurringActivities,self).write(vals)
        domain = [('sh_activity_id', '=', self.id)]
        find_to_unlink = self.env['mail.activity'].search(domain)
        for data in find_to_unlink:
            data.unlink()
        self.create_activity_recurring()
        return res

    def create_activity_recurring(self):
        today = datetime.date.today()
        event_starts_from = today
        if self.reference != None:
            domain = [('model', '=', self.reference._name)]
            res_model_id = self.env['ir.model'].search(domain,limit=1)
            domain = [('name', '=', )]
            start_time = float_to_time(self.sh_time_deadline)
            if self.end_type == 'count':
                if self.rrule_type == 'daily':
                    first = False
                    for i in range(0,self.count):
                        if not first:
                            pass
                            first = True
                        else:
                            event_starts_from = event_starts_from + datetime.timedelta(days=self.interval)
                        vals = {
                            'user_id' : self.user_id.id,
                            'date_deadline' : event_starts_from,
                            'summary' : self.summary,
                            'note' : self.description,
                            'activity_type_id' : self.activity_id.id,
                            'res_id' : self.reference.id,
                            'res_model' : self.reference._name,
                            'res_model_id':res_model_id.id,
                            'sh_activity_id' : self.id,
                            'sh_activity_tags' : self.sh_activity_tags.ids,
                            'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                            'sh_user_ids' : self.sh_user_ids.ids,
                            'supervisor_id' : self.supervisor_id.id,
                            'sh_date_deadline' : datetime.datetime.combine(event_starts_from,start_time)
                        }
                        self.env['mail.activity'].create(vals)
                elif self.rrule_type == 'weekly':
                    for i in range(0,self.count):
                        final_execution_date = False
                        born = event_starts_from.weekday()
                        born_day = calendar.day_name[born]
                        week_days_dict = {
                            'Monday' : 'mo',
                            'Tuesday' : 'tu',
                            'Wednesday' : 'we',
                            'Thursday' : 'th',
                            'Friday' : 'fr',
                            'Saturday' : 'sa',
                            'Sunday' : 'su'
                        }
                        for days,short in week_days_dict.items():
                            if not final_execution_date:
                                if born_day == days:
                                    if self['%s' % short]:
                                        final_execution_date = event_starts_from
                                        break
                        if not final_execution_date:
                            final_execution_date = self.recu(event_starts_from)
                        if final_execution_date:
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date,start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            event_starts_from = final_execution_date + datetime.timedelta(days=1)

                elif self.rrule_type == 'monthly':
                    final_execution_date = False
                    for i in range(0,self.count):
                        if self.month_by == 'date':
                            if not final_execution_date:
                                today_count = today.day
                                if today_count < self.day:
                                    add_date = self.day - today_count
                                    final_execution_date = event_starts_from + datetime.timedelta(days=add_date)
                                else:
                                    current_month = today.month
                                    year = today.year
                                    if current_month == 12:
                                        year += 1
                                        current_month = 1
                                    else:
                                        current_month += 1
                                    dates = '%s/%s/%s' %(self.day,current_month,year)
                                    final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")                        
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date,start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            if self.interval > 0:
                                final_execution_date = final_execution_date + relativedelta(months=+self.interval)
                            else:
                                final_execution_date = final_execution_date + relativedelta(months=+1)
                        elif self.month_by == 'day':
                            if not final_execution_date:
                                c = calendar.Calendar(firstweekday=calendar.SUNDAY)
                                weekday_label = dict(WEEKDAY_SELECTION)[self.weekday]
                                buu_day = int(self.byday) - 1
                                if weekday_label.upper() == 'FRIDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.FRIDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'MONDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.MONDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'TUESDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.TUESDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'WEDNESDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.WEDNESDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'THURSDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.THURSDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'SATURDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SATURDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'SUNDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SUNDAY and day.month == datetime.datetime.today().month][buu_day]
                                if ex_date:
                                    today_count = today.day
                                    if today_count < ex_date.day:
                                        add_date = ex_date.day - today_count
                                        final_execution_date = ex_date + datetime.timedelta(days=add_date)
                                    else:
                                        final_execution_date = ex_date + relativedelta(months=+1)
                                        final_execution_date = self.get_month_by_date(final_execution_date)
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date,start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            if self.interval > 0:
                                final_execution_date = final_execution_date + relativedelta(months=+self.interval)
                                final_execution_date = self.get_month_by_date(final_execution_date)
                            else:
                                final_execution_date = final_execution_date + relativedelta(months=+1)
                                final_execution_date = self.get_month_by_date(final_execution_date)
                elif self.rrule_type == 'yearly':
                    final_execution_date = False
                    for i in range(0,self.count):
                        if not final_execution_date:
                            year_count = {
                                'Jan' : 1,
                                'Feb' : 2,
                                'Mar' : 3,
                                'Apr' : 4,
                                'May' : 5,
                                'Jun' : 6,
                                'Jul' : 7,
                                'Aug' : 8,
                                'Sep' : 9,
                                'Oct' : 10,
                                'Nov' : 11,
                                'Dec' : 12,
                            }
                            for month,cu in year_count.items():
                                if month == self.month_year:
                                    exe_month = cu
                                    break
                            today_month = today.month
                            if today_month == exe_month:
                                today_count = today.day
                                if today_count < self.day:
                                    add_date = self.day - today_count
                                    final_execution_date = event_starts_from + datetime.timedelta(days=add_date)
                                else:
                                    current_month = today.month
                                    year = today.year
                                    if current_month == 12:
                                        year += 1
                                        current_month = 1
                                    else:
                                        current_month += 1
                                    dates = '%s/%s/%s' %(self.day,current_month,year)
                                    final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                            elif today_month < exe_month:
                                add_month = exe_month - today_month
                                some_day_month = event_starts_from + relativedelta(months=+add_month)
                                dates = '%s/%s/%s' %(self.day,some_day_month,today.year)
                                final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                            else:
                                current_year = today.year
                                current_year += 1
                                dates = '%s/%s/%s' %(self.day,exe_month,current_year)
                                final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                        vals = {
                            'user_id' : self.user_id.id,
                            'date_deadline' : final_execution_date,
                            'summary' : self.summary,
                            'note' : self.description,
                            'activity_type_id' : self.activity_id.id,
                            'res_id' : self.reference.id,
                            'res_model' : self.reference._name,
                            'res_model_id':res_model_id.id,
                            'sh_activity_id' : self.id,
                            'sh_activity_tags' : self.sh_activity_tags.ids,
                            'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                            'sh_user_ids' : self.sh_user_ids.ids,
                            'supervisor_id' : self.supervisor_id.id,
                            'sh_date_deadline' : datetime.datetime.combine(final_execution_date,start_time)
                        }
                        self.env['mail.activity'].create(vals)
                        if self.interval > 0:
                            final_execution_date = final_execution_date + relativedelta(years=+self.interval)
                        else:
                            final_execution_date = final_execution_date + relativedelta(years=+1)
            elif self.end_type == 'end_date':
                if self.rrule_type == 'daily':
                    first = False
                    while True:
                        if not first:
                            pass
                            first = True
                        else:
                            event_starts_from = event_starts_from + datetime.timedelta(days=self.interval)
                        vals = {
                            'user_id' : self.user_id.id,
                            'date_deadline' : event_starts_from,
                            'summary' : self.summary,
                            'note' : self.description,
                            'activity_type_id' : self.activity_id.id,
                            'res_id' : self.reference.id,
                            'res_model' : self.reference._name,
                            'res_model_id':res_model_id.id,
                            'sh_activity_id' : self.id,
                            'sh_activity_tags' : self.sh_activity_tags.ids,
                            'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                            'sh_user_ids' : self.sh_user_ids.ids,
                            'supervisor_id' : self.supervisor_id.id,
                            'sh_date_deadline' : datetime.datetime.combine(event_starts_from,start_time)
                        }
                        self.env['mail.activity'].create(vals)
                        if event_starts_from > self.until:
                            break
                elif self.rrule_type == 'weekly':
                    while True:
                        final_execution_date = False
                        born = event_starts_from.weekday()
                        born_day = calendar.day_name[born]
                        week_days_dict = {
                            'Monday' : 'mo',
                            'Tuesday' : 'tu',
                            'Wednesday' : 'we',
                            'Thursday' : 'th',
                            'Friday' : 'fr',
                            'Saturday' : 'sa',
                            'Sunday' : 'su'
                        }
                        for days,short in week_days_dict.items():
                            if not final_execution_date:
                                if born_day == days:
                                    if self['%s' % short]:
                                        final_execution_date = event_starts_from
                                        break
                        if not final_execution_date:
                            final_execution_date = self.recu(event_starts_from)
                        if final_execution_date:
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date,start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            event_starts_from = final_execution_date + datetime.timedelta(days=1)
                        if final_execution_date > self.until:
                            break
                elif self.rrule_type == 'monthly':
                    final_execution_date = False
                    while True:
                        if self.month_by == 'date':
                            if not final_execution_date:
                                today_count = today.day
                                if today_count < self.day:
                                    add_date = self.day - today_count
                                    final_execution_date = event_starts_from + datetime.timedelta(days=add_date)
                                else:
                                    current_month = today.month
                                    current_month += 1
                                    dates = '%s/%s/%s' %(self.day,current_month,today.year)
                                    final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date.date(),start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            if self.interval > 0:
                                final_execution_date = final_execution_date + relativedelta(months=+self.interval)
                            else:
                                final_execution_date = final_execution_date + relativedelta(months=+1)
                        elif self.month_by == 'day':
                            if not final_execution_date:
                                c = calendar.Calendar(firstweekday=calendar.SUNDAY)
                                weekday_label = dict(WEEKDAY_SELECTION)[self.weekday]
                                buu_day = int(self.byday) - 1
                                if weekday_label.upper() == 'FRIDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.FRIDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'MONDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.MONDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'TUESDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.TUESDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'WEDNESDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.WEDNESDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'THURSDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.THURSDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'SATURDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SATURDAY and day.month == datetime.datetime.today().month][buu_day]
                                elif weekday_label.upper() == 'SUNDAY':
                                    monthcal = c.monthdatescalendar(datetime.datetime.today().year, datetime.datetime.today().month)
                                    ex_date = [day for week in monthcal for day in week if day.weekday() == calendar.SUNDAY and day.month == datetime.datetime.today().month][buu_day]
                                if ex_date:
                                    today_count = today.day
                                    if today_count < ex_date.day:
                                        add_date = ex_date.day - today_count
                                        final_execution_date = ex_date + datetime.timedelta(days=add_date)
                                    else:
                                        final_execution_date = ex_date + relativedelta(months=+1)
                                        final_execution_date = self.get_month_by_date(final_execution_date)
                            vals = {
                                'user_id' : self.user_id.id,
                                'date_deadline' : final_execution_date,
                                'summary' : self.summary,
                                'note' : self.description,
                                'activity_type_id' : self.activity_id.id,
                                'res_id' : self.reference.id,
                                'res_model' : self.reference._name,
                                'res_model_id':res_model_id.id,
                                'sh_activity_id' : self.id,
                                'sh_activity_tags' : self.sh_activity_tags.ids,
                                'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                                'sh_user_ids' : self.sh_user_ids.ids,
                                'supervisor_id' : self.supervisor_id.id,
                                'sh_date_deadline' : datetime.datetime.combine(final_execution_date.date(),start_time)
                            }
                            self.env['mail.activity'].create(vals)
                            if self.interval > 0:
                                final_execution_date = final_execution_date + relativedelta(months=+self.interval)
                                final_execution_date = self.get_month_by_date(final_execution_date)
                            else:
                                final_execution_date = final_execution_date + relativedelta(months=+1)
                                final_execution_date = self.get_month_by_date(final_execution_date)
                        if final_execution_date.date() > self.until:
                            break
                elif self.rrule_type == 'yearly':
                    final_execution_date = False
                    while True:
                        if not final_execution_date:
                            year_count = {
                                'Jan' : 1,
                                'Feb' : 2,
                                'Mar' : 3,
                                'Apr' : 4,
                                'May' : 5,
                                'Jun' : 6,
                                'Jul' : 7,
                                'Aug' : 8,
                                'Sep' : 9,
                                'Oct' : 10,
                                'Nov' : 11,
                                'Dec' : 12,
                            }
                            for month,cu in year_count.items():
                                if month == self.month_year:
                                    exe_month = cu
                                    break
                            today_month = today.month
                            if today_month == exe_month:
                                today_count = today.day
                                if today_count < self.day:
                                    add_date = self.day - today_count
                                    final_execution_date = event_starts_from + datetime.timedelta(days=add_date)
                                else:
                                    current_month = today.month
                                    current_month += 1
                                    dates = '%s/%s/%s' %(self.day,current_month,today.year)
                                    final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                            elif today_month < exe_month:
                                add_month = exe_month - today_month
                                some_day_month = event_starts_from + relativedelta(months=+add_month)
                                dates = '%s/%s/%s' %(self.day,some_day_month,today.year)
                                final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                            else:
                                current_year = today.year
                                current_year += 1
                                dates = '%s/%s/%s' %(self.day,exe_month,current_year)
                                final_execution_date = datetime.datetime.strptime(dates, "%d/%m/%Y")
                        vals = {
                            'user_id' : self.user_id.id,
                            'date_deadline' : final_execution_date,
                            'summary' : self.summary,
                            'note' : self.description,
                            'activity_type_id' : self.activity_id.id,
                            'res_id' : self.reference.id,
                            'res_model' : self.reference._name,
                            'res_model_id':res_model_id.id,
                            'sh_activity_id' : self.id,
                            'sh_activity_tags' : self.sh_activity_tags.ids,
                            'sh_activity_alarm_ids' : self.sh_activity_alarm_ids.ids,
                            'sh_user_ids' : self.sh_user_ids.ids,
                            'supervisor_id' : self.supervisor_id.id,
                            'sh_date_deadline' : datetime.datetime.combine(final_execution_date.date(),start_time)
                        }
                        self.env['mail.activity'].create(vals)
                        if self.interval > 0:
                            final_execution_date = final_execution_date + relativedelta(years=+self.interval)
                        else:
                            final_execution_date = final_execution_date + relativedelta(years=+1)
                        if final_execution_date.date() > self.until:
                            break
